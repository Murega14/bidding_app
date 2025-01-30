from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime, timezone
from enum import Enum

db = SQLAlchemy()

class ProductStatus(Enum):
    AVAILABLE = 'available'
    SOLD = 'sold'
    
class BaseModel(db.Model):
    __abstract__ = True
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=True)

class UserMixin:
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone_number = db.Column(db.String(15), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    def hash_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @hybrid_property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class Admin(BaseModel, UserMixin):
    __tablename__ = 'admin'
    
    product = db.relationship('Product', back_populates='admin', lazy='selectin', cascade='all, delete-orphan')



class User(BaseModel, UserMixin):
    __tablename__ = 'users'
    
    bids = db.relationship('Bid', back_populates='user', lazy='selectin')
    


class Product(BaseModel):
    __tablename__ = 'products'
    
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String(), nullable=False)
    starting_price = db.Column(db.Numeric(10, 2), nullable=False)
    bidding_end_time = db.Column(db.DateTime, nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'))
    status = db.Column(db.Enum(ProductStatus), nullable=False, default=ProductStatus.AVAILABLE)
    
    admin = db.relationship('Admin', back_populates='product')
    
class Bid(BaseModel):
    __tablename__ = 'bids'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    bid_price = db.Column(db.Numeric(10, 2), nullable=False, unique=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    
    user = db.relationship('User', back_populates='bids')
