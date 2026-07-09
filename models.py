
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import uuid
import secrets
from datetime import datetime
db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(150))
    email = db.Column(db.String(150), unique=True)
    phone = db.Column(db.String(20))
    password = db.Column(db.String(200))

    # Contribution Wallet
    referral_contribution_balance = db.Column(db.Float, default=0.0)

    # Withdrawal status for current membership
    withdrawal_unlocked = db.Column(db.Boolean, default=False)

    contribution_deducted = db.Column(
    db.Boolean,
    default=False
    )
    
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
    is_admin = db.Column(
    db.Boolean,
    default=False
    )
    profile_image = db.Column(
        db.String(255),
        nullable=True
    )

    joined_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )
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
    account_active = db.Column(
    db.Boolean,
    default=True
    )

    notifications = db.relationship(
        "Notification",
        backref="user",
        lazy=True
    )
    last_contribution_period = db.Column(
    db.DateTime,
    nullable=True
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
    # referral_commission
    # task_reward
    # team_bonus
    # recharge
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






class Task(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(150), nullable=False)

    description = db.Column(db.Text)

    reward = db.Column(db.Float, nullable=False)

    vip_level = db.Column(db.String(20), nullable=False)

    url = db.Column(db.String(255))

    active = db.Column(db.Boolean, default=True)

    daily_limit = db.Column(db.Integer, default=1)

    video_duration = db.Column(db.Integer, default=30)


class UserTask(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    task_id = db.Column(
        db.Integer,
        db.ForeignKey("task.id"),
        nullable=False
    )

    completed_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    reward_paid = db.Column(
        db.Boolean,
        default=False
    )


class TaskSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    task_id = db.Column(db.Integer)

    started_at = db.Column(db.DateTime, default=datetime.utcnow)

    completed = db.Column(db.Boolean, default=False)

    watched_seconds = db.Column(db.Integer, default=0)

    session_token = db.Column(db.String(64),
        default=lambda: secrets.token_hex(32),
        unique=True
    )

class ContributionHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    referred_user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    amount = db.Column(db.Float, nullable=False)

    description = db.Column(db.String(200))

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    sponsor = db.relationship(
        "User",
        foreign_keys=[user_id]
    )

    referral = db.relationship(
        "User",
        foreign_keys=[referred_user_id]
    )


class MembershipHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    vip_level = db.Column(db.String(20))

    contribution_used = db.Column(db.Float)

    renewed_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    withdrawal_unlocked = db.Column(
        db.Boolean,
        default=False
    )

class Withdrawal(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    phone = db.Column(db.String(20), nullable=False)

    amount = db.Column(db.Float, nullable=False)

    # Which wallet the withdrawal came from
    wallet = db.Column(
        db.String(20),
        default="main"
    )

    status = db.Column(
        db.String(20),
        default="Pending"
    )
    # Pending
    # Approved
    # Rejected
    # Paid

    mpesa_receipt = db.Column(
        db.String(50),
        nullable=True
    )

    reference = db.Column(
        db.String(50),
        unique=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    processed_at = db.Column(
        db.DateTime,
        nullable=True
    )

    # Admin notes if rejected
    admin_note = db.Column(
        db.Text,
        nullable=True
    )
    intasend_transaction_id = db.Column(
    db.String(100),
    nullable=True
    )
