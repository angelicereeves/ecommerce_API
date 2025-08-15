# all imports
from __future__ import annotations
from typing import List, Optional
from datetime import datetime

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from marshmallow import ValidationError, validates, validate, fields
from sqlalchemy import (
    ForeignKey, Table, Column, String, Integer, Float, DateTime,
    UniqueConstraint, select
)
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from sqlalchemy.exc import IntegrityError
import os


# Flask & DB config
app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'mysql+mysqlconnector://root:0829AmDAjD23%3C3%21@localhost/ecommerce_api'
)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# Declarative base
class Base(DeclarativeBase):
    pass


# Initialize extensions
db = SQLAlchemy(model_class=Base)
db.init_app(app)
ma = Marshmallow(app)


# Association table with duplicate prevention
order_product = Table(
    'order_product',
    Base.metadata,
    Column('order_id', ForeignKey('orders.id'), primary_key=True),
    Column('product_id', ForeignKey('products.id'), primary_key=True),
    UniqueConstraint('order_id', 'product_id', name='uq_order_product')  # no duplicates
)


# DB Models

# users
class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    orders: Mapped[List['Order']] = relationship(
        'Order', back_populates='user', cascade='all, delete-orphan'
    )


# orders
class Order(Base):
    __tablename__ = 'orders'
    id: Mapped[int] = mapped_column(primary_key=True)
    order_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    user: Mapped['User'] = relationship('User', back_populates='orders')

    products: Mapped[List['Product']] = relationship(
        'Product', secondary=order_product, back_populates='orders'
    )


# products
class Product(Base):
    __tablename__ = 'products'
    id: Mapped[int] = mapped_column(primary_key=True)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)

    orders: Mapped[List['Order']] = relationship(
        'Order', secondary=order_product, back_populates='products'
    )


# Schemas (validation + serialization)

class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User

    name = ma.auto_field(required=True, validate=validate.Length(min=1))
    email = fields.Email(required=True)  # email format validation
    address = ma.auto_field(required=False, allow_none=True) # not required


class ProductSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Product

    product_name = ma.auto_field(required=True, validate=validate.Length(min=1)) # validate that its at least one character
    price = ma.auto_field(required=True)

    @validates("price")
    def validate_price(self, value):
        if value < 0:
            raise ValidationError("Price must be non-negative.")


class OrderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Order
        include_fk = True  # include user_id

    # Make order_date required
    order_date = fields.DateTime(required=True)


# Initialize schemas
user_schema = UserSchema()
users_schema = UserSchema(many=True)
product_schema = ProductSchema()
products_schema = ProductSchema(many=True)
order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)


# Error handling
@app.errorhandler(ValidationError)
def handle_validation_error(err: ValidationError):
    return jsonify(err.messages), 400


# init message
@app.route('/')
def root():
    return jsonify({'status': 'ok', 'message': 'E-commerce API running'})

@app.route('/initdb', methods=['POST'])
def initdb():
    with app.app_context():
        db.create_all()
    return jsonify({'message': 'Database tables created.'}), 201


# USER endpoints

# POST users
@app.route('/users', methods=['POST'])
def create_user():
    data = request.get_json() or {}
    try:
        loaded = user_schema.load(data)
    except ValidationError as e:
        return jsonify(e.messages), 400

    # unique email
    existing = db.session.execute(
        select(User).where(User.email == loaded['email'])
    ).scalar_one_or_none()
    if existing:
        return jsonify({'message': 'Email already exists'}), 400

    user = User(
        name=loaded['name'],
        email=loaded['email'],
        address=loaded.get('address')
    )
    db.session.add(user)
    db.session.commit()
    return user_schema.jsonify(user), 201


# GET users
@app.route('/users', methods=['GET'])
def get_users():
    users = db.session.execute(select(User)).scalars().all()
    return users_schema.jsonify(users), 200


# GET user_id
@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id: int):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'message': 'Invalid user id'}), 400
    return user_schema.jsonify(user), 200


# PUT user_id (partial updates allowed)
@app.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id: int):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'message': 'Invalid user id'}), 400

    try:
        payload = user_schema.load(request.get_json() or {}, partial=True)
    except ValidationError as e:
        return jsonify(e.messages), 400

    # unique email check if changed
    if 'email' in payload and payload['email'] != user.email:
        exists = db.session.execute(
            select(User).where(User.email == payload['email'])
        ).scalar_one_or_none()
        if exists:
            return jsonify({'message': 'Email already exists'}), 400

    user.name = payload.get('name', user.name)
    user.email = payload.get('email', user.email)
    user.address = payload.get('address', user.address)
    db.session.commit()
    return user_schema.jsonify(user), 200


# DELETE user_id
@app.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id: int):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'message': 'Invalid user id'}), 400
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': f'successfully deleted user {user_id}'}), 200


# PRODUCT endpoints

# POST products
@app.route('/products', methods=['POST'])
def create_product():
    try:
        data = product_schema.load(request.get_json() or {})
    except ValidationError as e:
        return jsonify(e.messages), 400

    product = Product(product_name=data['product_name'], price=data['price'])
    db.session.add(product)
    db.session.commit()
    return product_schema.jsonify(product), 201


# GET products
@app.route('/products', methods=['GET'])
def get_products():
    products = db.session.execute(select(Product)).scalars().all()
    return products_schema.jsonify(products), 200


# GET product_id
@app.route('/products/<int:product_id>', methods=['GET'])
def get_product(product_id: int):
    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({'message': 'Invalid product id'}), 400
    return product_schema.jsonify(product), 200


# PUT product_id (partial updates allowed)
@app.route('/products/<int:product_id>', methods=['PUT'])
def update_product(product_id: int):
    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({'message': 'Invalid product id'}), 400

    try:
        payload = product_schema.load(request.get_json() or {}, partial=True) #partial updates allowed
    except ValidationError as e:
        return jsonify(e.messages), 400

    product.product_name = payload.get('product_name', product.product_name)
    product.price = payload.get('price', product.price)
    db.session.commit()
    return product_schema.jsonify(product), 200


# DELETE product_id
@app.route('/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id: int):
    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({'message': 'Invalid product id'}), 400
    db.session.delete(product)
    db.session.commit()
    return jsonify({'message': f'successfully deleted product {product_id}'}), 200


# ORDER endpoints

# POST orders (requires user_id and order_date)
@app.route('/orders', methods=['POST'])
def create_order():
    payload = request.get_json() or {}

    # Marshmallow validation 
    try:
        data = order_schema.load(payload)
    except ValidationError as e:
        return jsonify(e.messages), 400

    
    order_date_val = data.get('order_date')
    if isinstance(order_date_val, str):
 
        try:
            order_date_val = datetime.fromisoformat(order_date_val)
        except ValueError:
            return jsonify({'message': 'Invalid order_date, use ISO 8601 like 2025-08-15T14:30:00'}), 400

    order = Order(
        user_id=data['user_id'],
        order_date=order_date_val or datetime.utcnow() # if not date is entered it will default to now
    )

    # (Optional) initial product_ids list
    product_ids: List[int] = payload.get('product_ids', []) or []
    if not isinstance(product_ids, list):
        return jsonify({'message': 'product_ids must be a list of integers'}), 400

    if product_ids:
        products = db.session.execute(
            select(Product).where(Product.id.in_(product_ids))
        ).scalars().all()
        found_ids = {p.id for p in products}
        missing = [pid for pid in product_ids if pid not in found_ids]
        if missing:
            return jsonify({'message': f'Products not found: {missing}'}), 404
        for p in products:
            if p not in order.products:
                order.products.append(p)

    db.session.add(order)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'message': 'Invalid user_id or foreign key constraint failed'}), 400

    return order_schema.jsonify(order), 201


# PUT add product to order
@app.route('/orders/<int:order_id>/add_product/<int:product_id>', methods=['PUT'])
def add_product_to_order(order_id: int, product_id: int):
    order = db.session.get(Order, order_id)
    product = db.session.get(Product, product_id)

    if not order or not product:
        return jsonify({'message': 'Invalid order or product id'}), 400

    if product in order.products:
        return jsonify({'message': 'Product already in order'}), 200

    order.products.append(product)
    db.session.commit()
    return order_schema.jsonify(order), 200


# DELETE remove product from order
@app.route('/orders/<int:order_id>/remove_product/<int:product_id>', methods=['DELETE'])
def remove_product_from_order(order_id: int, product_id: int):
    order = db.session.get(Order, order_id)
    product = db.session.get(Product, product_id)

    if not order or not product:
        return jsonify({'message': 'Invalid order or product id'}), 400

    if product not in order.products:
        return jsonify({'message': 'Product not in order'}), 404

    order.products.remove(product)
    db.session.commit()
    return order_schema.jsonify(order), 200


# GET all orders for a user
@app.route('/orders/user/<int:user_id>', methods=['GET'])
def get_orders_for_user(user_id: int):
    q = select(Order).where(Order.user_id == user_id).order_by(Order.order_date.desc())
    orders = db.session.execute(q).scalars().all()
    return orders_schema.jsonify(orders), 200


# GET products for an order
@app.route('/orders/<int:order_id>/products', methods=['GET'])
def get_products_for_order(order_id: int):
    order = db.session.get(Order, order_id)
    if not order:
        return jsonify({'message': 'Invalid order id'}), 400
    return products_schema.jsonify(order.products), 200




# Run
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

