from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, manager, master

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    orders = db.relationship('Order', backref='client', lazy=True)

class OrderStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    washing_machine_model = db.Column(db.String(100), nullable=False)
    condition = db.Column(db.Text)
    description = db.Column(db.Text)
    purchase_price = db.Column(db.Float)
    repair_costs = db.Column(db.Float)
    sale_price = db.Column(db.Float)
    status_id = db.Column(db.Integer, db.ForeignKey('order_status.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    completed_at = db.Column(db.DateTime)
    status = db.relationship('OrderStatus', backref='orders')

class SparePart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    article = db.Column(db.String(50), unique=True)
    quantity = db.Column(db.Integer, default=0)
    cost_price = db.Column(db.Float)
    retail_price = db.Column(db.Float)
    min_stock = db.Column(db.Integer, default=5)

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    salary = db.Column(db.Float)
    hire_date = db.Column(db.DateTime, default=datetime.now)