
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import uuid
from datetime import datetime
db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(150))
    email = db.Column(db.String(150), unique=True)
    phone = db.Column(db.String(20))
    password = db.Column(db.String(200))

    # Referral System
    referral_code = db.Column(
        db.String(20),
        unique=True,
        default=lambda: str(uuid.uuid4())[:8]
    )

    referred_by = db.Column(
        db.String(20),
        nullable=True
    )
    
    notifications = db.relationship(
        "Notification",
        backref="user",
        lazy=True
    )


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), nullable=False)
    transaction_code = db.Column(db.String(50), nullable=True)
    amount = db.Column(db.Integer, default=10)
    status = db.Column(db.String(20), default="pending")
    email = db.Column(db.String(120))


class PendingUser(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(100), nullable=False)

    email = db.Column(db.String(120), nullable=False)

    phone = db.Column(db.String(20), nullable=False)

    password = db.Column(db.String(255), nullable=False)

    referred_by = db.Column(
        db.String(20),
        nullable=True
    )
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    title = db.Column(db.String(100))

    message = db.Column(db.Text)

    is_read = db.Column(db.Boolean, default=False)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


