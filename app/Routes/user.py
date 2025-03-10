from flask import Blueprint, request, jsonify
import logging
from ..models import db, User, Product, Bid
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from datetime import timedelta, datetime, timezone

user = Blueprint('user', __name__)

logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@user.route('/api/v1/user/signup', methods=['POST'])
def signup_user():
    """
    create a user account
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
        
        if db.session.query(User).filter((User.email==email) | (User.phone_number==phone_number)).first():
            logger.error(f"phone number{phone_number} or email{email} exists")
            return jsonify({"error": "email or phone number exists"}), 409
            
        
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone_number=phone_number
        )
        new_user.hash_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        logger.info(f"new admin account has been created")
        return jsonify({"success": "Account created"}), 200
    
    except Exception as e:
        logger.error(f"failed to create account: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "internal server error"}), 500
    
@user.route('/api/v1/user/login',methods=['POST'])
def login_user():
    """
    login into an existing user account
    """
    try:
        data  = request.get_json()
        identifier = data.get('identifier')
        password = data.get('password')
        
        if not all([identifier, password]):
            return jsonify({"error": "Missing required fields"}), 400
            
        user = User.query.filter(
            (User.email == identifier) | 
            (User.phone_number == identifier)
        ).first()
        
        if not user or not user.check_password(password):
            return jsonify({"error": "Invalid credentials"}), 401
        
        identity = str(user.id)
        expires = timedelta(hours=2)
        access_token = create_access_token(
            identity=identity,
            expires_delta=expires
        )
        refresh_token = create_refresh_token(user.id)
        
        response = jsonify({
            "success": True,
            "message": "Login successful",
            "token": access_token,
        })
        
        return response
    
    except Exception as e:
        logger.error(f"failed to login user: {user.id},{str(e)}")
        return jsonify({"error": "failed to login user"})
    
@user.route('/api/v1/products', methods=['GET'])
def view_products():
    """
    view all products
    """
    try:
        products = Product.query.all()
        
        product_list = []
        for product in products:
            # when displaying the product i am going to first check if a bid exists
            #if it does i am going to check for the highest amount that has been bid and display it
            #if a bid does not exist i am going to display the starting price
            highest_bid = Bid.query.filter_by(product_id=product.id).order_by(Bid.bid_price.desc()).first()
            
            current_price = highest_bid.bid_price if highest_bid else product.starting_price
            
            product_list.append({
                "name": product.name,
                "description": product.description,
                "price": current_price,
                "bidding_end_time": product.bidding_end_time,
                "owner": product.admin.full_name
            })
            
        return jsonify(product_list), 200
    
    except Exception as e:
        logger.error(f"failed to fetch products: {str(e)}")
        return jsonify({"error": "internal server error"}), 500
    
@user.route('/api/v1/products/<int:id>/bid', methods=['POST'])
@jwt_required()
def make_bid(id: int):
    """
    make a bid

    Args:
        id (int): product identifier
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            logger.error(f"user {user_id} does not exist")
            return jsonify({"error": "user not found"}), 404
        
        product = Product.query.get(id)
        if not product:
            logger.error(f"product {id} does not exist")
            return jsonify({"error": "product not found"}), 404
        
        if product.bidding_end_time.tzinfo is None:
            product.bidding_end_time = product.bidding_end_time.replace(tzinfo=timezone.utc)
            
        current_time = datetime.now(timezone.utc)
        
        if current_time > product.bidding_end_time:
            logger.error("bid time has elapsed, cannot make bid")
            return jsonify({"error": "bidding time has elapsed"}), 400
        
        data = request.get_json()
        bid_price = data.get('price')
        
        if bid_price is None:
            logger.error("bid price is missing")
            return jsonify({"error": "bid price is required"}), 400
        
        highest_bid = Bid.query.filter_by(product_id=id).order_by(Bid.bid_price.desc()).first()
        
        # If there are no bids, compare with the starting price
        if highest_bid is None:
            if bid_price <= product.starting_price:
                logger.error(f"bid price {bid_price} is lower than or equal to the starting price {product.starting_price}")
                return jsonify({"error": "cannot make a bid lower than or equal to the starting price"}), 403
        else:
            if bid_price <= highest_bid.bid_price:
                logger.error(f"bid price {bid_price} is lower than or equal to the current highest bid {highest_bid.bid_price}")
                return jsonify({"error": "cannot make a bid lower than or equal to the current bid"}), 403
        
        new_bid = Bid(
            product_id=id,
            user_id=user_id,
            bid_price=bid_price
        )
        db.session.add(new_bid)
        db.session.commit()
        
        logger.info(f"user {user_id} bid {bid_price} on product {id}")
        return jsonify({"message": "bid placed successfully"}), 201
    
    except Exception as e:
        logger.error(f"failed to bid on product: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "internal server error"}), 500