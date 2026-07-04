
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

    # ================= WALLETS =================
    
    main_wallet = db.Column(db.Float, default=0)
    
    task_wallet = db.Column(db.Float, default=0)
    
    team_wallet = db.Column(db.Float, default=0)
    
    withdrawn = db.Column(db.Float, default=0)
    commissions = db.Column(db.Float, default=0)
    # ================= ACCOUNT =================

    vip_level = db.Column(
        db.String(20),
        default="Bronze"
    )

    profile_image = db.Column(
        db.String(255),
        nullable=True
    )

    joined_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
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

    amount = db.Column(db.Float, nullable=False)

    status = db.Column(
        db.String(20),
        default="pending"
    )

    email = db.Column(db.String(120))

    # NEW
    payment_type = db.Column(
        db.String(20),
        default="registration"
    )

    # NEW
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=True
    )


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

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    transaction_type = db.Column(db.String(30))
    # deposit
    # withdrawal
    # referral_bonus
    # task_reward
    # aviator_win
    # aviator_loss

    amount = db.Column(db.Float, nullable=False)

    wallet = db.Column(db.String(20))
    # main
    # task
    # team

    status = db.Column(
        db.String(20),
        default="Completed"
    )

    description = db.Column(db.String(255))

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


from datetime import date

tasks_completed = db.Column(db.Integer, default=0)

last_task_date = db.Column(
    db.Date,
    nullable=True
)

vip_started_at = db.Column(
    db.DateTime,
    nullable=True
)

vip_expires_at = db.Column(
    db.DateTime,
    nullable=True
)

class Task(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(150))

    description = db.Column(db.Text)

    reward = db.Column(db.Float)

    vip_level = db.Column(db.String(20))

    url = db.Column(db.String(255))

    active = db.Column(db.Boolean, default=True)


class UserTask(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id")
    )

    task_id = db.Column(
        db.Integer,
        db.ForeignKey("task.id")
    )

    completed_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )