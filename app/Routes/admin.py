from flask import Blueprint, request, jsonify
import logging
from ..models import db, Admin, Product, Bid
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import timedelta, datetime, timezone

admin = Blueprint('admin', __name__)

logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)



@admin.route('/api/v1/signup', methods=['POST'])
def signup_admin():
    """
    create an admin account
    """
    try:
        data = request.get_json()
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        email = data.get('email')
        phone_number = data.get('phone_number')
        password = data.get('password')
        
        if not all([first_name, last_name, email, phone_number, password]):
            logger.error("all fields have not been entered")
            return jsonify({"error": "all fields are required"}), 401
        
        if db.session.query(Admin).filter((Admin.email==email) | (Admin.phone_number==phone_number)).first():
            logger.error(f"phone number {phone_number} or email {email} exists")
            return jsonify({"error": "email or phone number exists"}), 409
            
        
        new_admin = Admin(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone_number=phone_number
        )
        new_admin.hash_password(password)
        db.session.add(new_admin)
        db.session.commit()
        
        logger.info(f"new admin account has been created")
        return jsonify({"success": "Account created"}), 200
    
    except Exception as e:
        logger.error(f"failed to create account: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "internal server error"}), 500
    
@admin.route('/api/v1/admin/login',methods=['POST'])
def login_admin():
    """
    login into an existing admin account
    """
    try:
        data  = request.get_json()
        identifier = data.get('identifier')
        password = data.get('password')
        
        if not all([identifier, password]):
            return jsonify({"error": "Missing required fields"}), 400
            
        admin = Admin.query.filter(
            (Admin.email == identifier) | 
            (Admin.phone_number == identifier)
        ).first()
        
        if not admin or not admin.check_password(password):
            return jsonify({"error": "Invalid credentials"}), 401
        
        identity = str(admin.id)
        expires = timedelta(hours=2)
        access_token = create_access_token(
            identity=identity,
            expires_delta=expires
        )
        response = jsonify({
            "success": True,
            "message": "Login successful",
            "token": access_token,
        })
        
        return response
    
    except Exception as e:
        logger.error(f"failed to login user: {admin.id} {str(e)}")
        
@admin.route('/api/v1/admin/product/add', methods=['POST'])
@jwt_required()
def create_product():
    """
    create a product by a logged in account
    
    Expected JSON format:
    {
        "name": "Product Name",
        "description": "Product Description",
        "starting_price": 100,
        "end_time": "dd/mm/yyyy hh:mm:ss"
    }
    """
    try:
        user_id = get_jwt_identity()
        user = Admin.query.get(user_id)
        if not user:
            logger.error(f"user {user_id} does not exist")
            return jsonify({"error": "user not found"}), 404
        
        data = request.get_json()
        name = data.get('name')
        description = data.get('description')
        starting_price = int(data.get('starting_price', 0)) 
        end_time = data.get('end_time')
        
        
        if not all([name, description, starting_price, end_time]):
            logger.error("not all fields have been entered")
            return jsonify({"error": "all fields are required"}), 401
        
        current_time = datetime.now(timezone.utc)
        end_time_obj = datetime.strptime(end_time, '%d/%m/%Y %H:%M:%S').replace(tzinfo=timezone.utc)
        
        if end_time_obj < current_time:
                return jsonify({
                    'status': 'error',
                    'message': 'Bid end time cannot be in the past'
                }), 400
        
        new_product = Product(
            name=name,
            description=description,
            starting_price=starting_price,
            bidding_end_time=end_time_obj,
            admin_id=user_id
        )
        db.session.add(new_product)
        db.session.commit()
        
        response = {
            "status": "success",
            "message": "Product created successfully",
            "data": {
                "product": {
                    "id": new_product.id,
                    "name": name,
                    "description": description,
                    "starting_price": float(starting_price),
                    "bidding_end_time": end_time_obj.strftime('%d/%m/%Y %H:%M:%S'),
                    "status": new_product.status.value,
                    "created_at": new_product.created_at.strftime('%d/%m/%Y %H:%M:%S')
                },
                "admin": {
                    "id": user.id,
                    "name": f"{user.first_name} {user.last_name}",
                    "email": user.email
                }
            }
        }
        
        logger.info(f"Product {new_product.id} created by admin {user_id}")
        return jsonify(response), 201
    
    except Exception as e:
        logger.error(f"failed to create product: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "internal server error"}),500
    
    
@admin.route('/api/v1/admin/<int:id>/end', methods=['PUT'])
@jwt_required()
def end_bid(id: int):
    """
    Endpoint for when a product owner/admin wants to manually end the bid.
    """
    try:
        user_id = int(get_jwt_identity())
        user = Admin.query.get(user_id)
        
        if not user:
            logger.error(f"User {user_id} does not exist")
            return jsonify({"error": "User not found"}), 404
        
        product = Product.query.get(id)
        if not product:
            logger.error(f"Product {id} not found")
            return jsonify({"error": "Product not found"}), 404
        
        if user.id != product.admin_id:
            logger.error(f"Unauthorized access by user {user_id} on product {id}")
            return jsonify({"error": "Unauthorized access"}), 403
        
        bid_time = datetime.now(timezone.utc)
        product.bidding_end_time = bid_time
        db.session.commit()
        
        logger.info('Bidding time updated and bidding stopped')
        return jsonify({"message": "Bidding stopped"}), 200
    
    except Exception as e:
        logger.error(f"Failed to stop bidding: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500
    
    
@admin.route('/api/v1/products/sold', methods=['GET'])
@jwt_required()
def view_sold_products():
    """
    view products that have been sold
    """
    try:
        sold_products = Product.query.filter_by(status="sold").all()
        
        product_list = []
        for product in sold_products:
            highest_bid = Bid.query.filter_by(product_id=product.id)\
                .order_by(Bid.bid_price.desc())\
                .first()
                
            winning_price = float(highest_bid.bid_price) if highest_bid else float(product.starting_price)
            
            product_list.append({
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "final_price": winning_price,
                "sold_at": product.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                "winning_bid": {
                    "user_id": highest_bid.user_id if highest_bid else None,
                    "bid_price": winning_price
                }
            })
            
        return jsonify({
            "status": "success",
            "sold_products": product_list
        }), 200
        
    except Exception as e:
        logger.error(f"Error viewing sold products: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve sold products"
        }), 500