from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150))
    email = db.Column(db.String(150), unique=True)
    phone = db.Column(db.String(20))
    password = db.Column(db.String(200))


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), nullable=False)
    transaction_code = db.Column(db.String(50), nullable=True)
    amount = db.Column(db.Integer, default=10)
    status = db.Column(db.String(20), default="pending")
