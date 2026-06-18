# Модели базы данных
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<User {self.username}>"


class Material(db.Model):
    __tablename__ = "materials"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    unit = db.Column(db.String(30), nullable=False)
    min_stock = db.Column(db.Float, default=0)
    current_stock = db.Column(db.Float, default=0)
    description = db.Column(db.Text)

    requests = db.relationship("SupplyRequest", backref="material", lazy=True)
    deliveries = db.relationship("Delivery", backref="material", lazy=True)

    def __repr__(self):
        return f"<Material {self.name}>"


class Supplier(db.Model):
    __tablename__ = "suppliers"

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(150), nullable=False)
    contact_person = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    notes = db.Column(db.Text)

    deliveries = db.relationship("Delivery", backref="supplier", lazy=True)

    def __repr__(self):
        return f"<Supplier {self.company_name}>"


class SupplyRequest(db.Model):
    __tablename__ = "supply_requests"

    id = db.Column(db.Integer, primary_key=True)
    request_number = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    initiator = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(120), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    priority = db.Column(db.String(50), nullable=False)
    comment = db.Column(db.Text)
    status = db.Column(db.String(50), nullable=False, default="новая")

    deliveries = db.relationship("Delivery", backref="request", lazy=True)

    def __repr__(self):
        return f"<SupplyRequest {self.request_number}>"


class Delivery(db.Model):
    __tablename__ = "deliveries"

    id = db.Column(db.Integer, primary_key=True)
    delivery_number = db.Column(db.String(50), unique=True, nullable=False)
    delivery_date = db.Column(db.DateTime, default=datetime.utcnow)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    request_id = db.Column(db.Integer, db.ForeignKey("supply_requests.id"), nullable=True)
    status = db.Column(db.String(50), nullable=False, default="доставлена")

    def __repr__(self):
        return f"<Delivery {self.delivery_number}>"