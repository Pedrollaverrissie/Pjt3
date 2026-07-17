from game_engine import game
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import re, random ,time,os,requests
from flask_mail import Mail, Message

from models import (
    db,
    User,
    Payment,
    PendingUser,
    Notification,
    Transaction,
    Task,
    UserTask,
    TaskSession,
    ContributionHistory,
    MembershipHistory,
    Withdrawal
)
from functools import wraps
from flask import abort

from flask_sqlalchemy import SQLAlchemy
from intasend import APIService
from dotenv import load_dotenv

from datetime import timedelta
from flask_migrate import Migrate



VIP_PLANS = {

    "Bronze": {
        "price": 200,
        "tasks": 1,
        "reward": 20,
        "withdrawal": 200,
        "required_referrals": 4
    },

    "Silver": {
        "price": 500,
        "tasks": 3,
        "reward": 16.67,
        "withdrawal": 500,
        "required_referrals": 3
    },

    "Gold": {
        "price": 1000,
        "tasks": 4,
        "reward": 25,
        "withdrawal": 1000,
        "required_referrals": 3
    },

    "Platinum": {
        "price": 2500,
        "tasks": 5,
        "reward": 50,
        "withdrawal": 2500,
        "required_referrals": 3
    },

    "Diamond": {
        "price": 5000,
        "tasks": 5,
        "reward": 100,
        "withdrawal": 5000,
        "required_referrals": 3
    }

}

VIP_ORDER = [
    "Bronze",
    "Silver",
    "Gold",
    "Platinum",
    "Diamond"
]


load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise Exception("DATABASE_URL environment variable is missing!")

if database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://",
        "postgresql://",
        1
    )

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=30)

INTASEND_PUBLISHABLE_KEY = os.getenv("INTASEND_PUBLISHABLE_KEY")
INTASEND_SECRET_KEY = os.getenv("INTASEND_SECRET_KEY")

service = APIService(
    token=INTASEND_SECRET_KEY,
    publishable_key=INTASEND_PUBLISHABLE_KEY,
    test=False
)

# ------------MAIL CONFIGURATION---------------
app.config['MAIL_SERVER'] = 'smtp-relay.brevo.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False

app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_USERNAME")

mail = Mail(app)
otp_store = {}

db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
#------------send_mpesa_withdrawal function------------
def send_mpesa_withdrawal(user, amount):
    """
    Sends an automatic M-Pesa withdrawal using IntaSend B2C.
    Returns:
        (True, response)  -> Request accepted
        (False, error)    -> Failed to initiate
    """

    try:

        transactions = [{
            "name": user.username,
            "account": user.phone,
            "amount": amount,
            "narrative": "Supernova Earn Withdrawal"
        }]

        response = service.transfer.mpesa(
            currency="KES",
            transactions=transactions,
            requires_approval="NO"
        )

        print("=" * 60)
        print("INTASEND WITHDRAWAL RESPONSE")
        print(response)
        print("=" * 60)

        status = response.get("status", "").lower()

        accepted_statuses = [
            "preview and approve",
            "confirming balance",
            "sending payment",
            "processing payment",
            "pending",
            "processing",
            "submitted"
        ]

        if status in accepted_statuses:
            return True, response

        return False, response

    except Exception as e:

        print("=" * 60)
        print("INTASEND WITHDRAWAL ERROR")
        print(e)
        print("=" * 60)

        return False, str(e)
#-----------USER LOADER--------------

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------- CREATE DB ----------------
with app.app_context():
    db.create_all()
    print("DATABASE TABLES CREATED")

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("home.html")


# ---------------- SIGNUP ----------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    # Get referral code from URL, e.g. /signup?ref=SN1
    ref = request.args.get("ref") or request.form.get("referral_code")

    # Validate referral code
    if ref:
        referrer = User.query.filter_by(referral_code=ref).first()
        if not referrer:
            ref = None

    if request.method == "POST":

        email = request.form["email"]
        phone = request.form["phone"]
        terms = request.form.get("terms")

        print("REFERRAL CODE:", ref)

        # Validation patterns
        email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        phone_pattern = r"^(07|01)\d{8}$"

        if not terms:
            return render_template("checkbox_alert.html")

        if not re.match(email_pattern, email):
            return "Invalid email format!"

        if not re.match(phone_pattern, phone):
            return "Invalid phone number!"

        # Convert 07xxxxxxxx to 2547xxxxxxxx
        if phone.startswith("0"):
            phone = "254" + phone[1:]

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            return "Email already exists! Please login."

        hashed_pw = generate_password_hash(
            request.form["password"]
        )

        # Save pending user together with who referred them
        pending_user = PendingUser(
            username=request.form["username"],
            email=email,
            phone=phone,
            password=hashed_pw,
            referred_by=ref
        )

        db.session.add(pending_user)
        db.session.commit()

        print("SIGNUP PASSED VALIDATION")
        print("USER SAVED:")
        print(pending_user.username)
        print(pending_user.email)
        print(pending_user.phone)
        print("REFERRED BY:", ref)

        return redirect("/payment")

    return render_template(
        "signup.html",
        ref=ref
    )

#............CHECHBOX ALERT..............

@app.route("/checkboxAlert")
def checkbox_alert():
    return render_template("checkbox_alert.html")
#---------------DECORATOR ACTIVE/SUSPEND HELPER----------
from functools import wraps
from flask_login import current_user, logout_user
from flask import redirect

def active_account_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):

        if not current_user.account_active:
            logout_user()
            return redirect("/login")

        return f(*args, **kwargs)

    return decorated
# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        login_input = request.form["login"]

        user = User.query.filter(
            (User.email == login_input) |
            (User.username == login_input)
        ).first()

        if user and check_password_hash(user.password, request.form["password"]):

            # Prevent suspended users from logging in
            if not user.account_active:
                return "Your account has been suspended. Contact support."

            remember = request.form.get("remember_me") == "on"

            login_user(user, remember=remember)

            return redirect("/dashboard")

        return render_template("invalid_login.html")

    return render_template("login.html")

#--------------PAYMENT-----------------

@app.route('/payment', methods=['GET', 'POST'])
def payment():

    if request.method == "POST":

        phone = request.form['phone'].strip()

        # Convert 07xxxxxxxx to 2547xxxxxxxx
        if phone.startswith("0"):
            phone = "254" + phone[1:]

        try:

            # Get latest pending user
            pending_user = PendingUser.query.order_by(
                PendingUser.id.desc()
            ).first()

            if not pending_user:
                return "No pending signup found"



            response = service.collect.mpesa_stk_push(
                phone_number=phone,
                amount=10,
                narrative="Account Activation"
            )

            print("IntaSend Response:", response)

            invoice_id = response["invoice"]["invoice_id"]

            payment = Payment(
                phone=phone,
                email=pending_user.email,
                transaction_code=invoice_id,
                amount=100,
                status="pending",
                payment_type="registration"
            )

            db.session.add(payment)
            db.session.commit()

            print("PAYMENT SAVED:")
            print(payment.email)
            print(payment.transaction_code)

            return render_template(
                "payment_pending.html",
                invoice_id=invoice_id
            )

        except Exception as e:
            print("Payment Error:", str(e))
            return f"Payment failed: {str(e)}"

    return render_template("payment.html")


# ---------------- DASHBOARD ----------------
from datetime import datetime

@app.route("/dashboard")
@login_required
@active_account_required
def dashboard():

    payments = Payment.query.filter_by(
        phone=current_user.phone
    ).all()

    total_paid = sum(
        p.amount for p in payments
        if p.status == "approved"
    )

    referral_link = (
        f"https://pjt3.onrender.com/signup?ref="
        f"{current_user.referral_code}"
    )

    total_referrals = User.query.filter_by(
        referred_by=current_user.referral_code
    ).count()

    # -----------------------------------
    # Total Successful Recharge Amount
    # -----------------------------------
    total_deposits = db.session.query(
        db.func.sum(Payment.amount)
    ).filter(
        Payment.user_id == current_user.id,
        Payment.payment_type == "recharge",
        Payment.status == "completed"
    ).scalar() or 0

    # -----------------------------------
    # Total Income
    # Main Wallet + Deposits
    # -----------------------------------
    total_income = current_user.main_wallet + total_deposits

    # -------------------------------
    # Automatically expire VIP
    # -------------------------------
    if (
        current_user.vip_level != "Free"
        and current_user.vip_expires_at
        and current_user.vip_expires_at <= datetime.utcnow()
    ):

        current_user.vip_level = "Free"
        current_user.vip_started_at = None
        current_user.vip_expires_at = None


        db.session.add(
            Notification(
                user_id=current_user.id,
                title="VIP Expired",
                message="Your VIP plan has expired. Recharge to continue enjoying premium tasks."
            )
        )

        db.session.commit()

    # -------------------------------
    # Days remaining
    # -------------------------------
    vip_days_left = 0

    if current_user.vip_expires_at:
        vip_days_left = (
            current_user.vip_expires_at - datetime.utcnow()
        ).days

    today_earnings = db.session.query(
        db.func.sum(Transaction.amount)
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_type == "task_reward",
        db.func.date(Transaction.created_at) == date.today()
    ).scalar() or 0

    return render_template(
        "dashboard.html",

        username=current_user.username,

        # Wallets
        main_wallet=current_user.main_wallet,
        withdrawable_wallet=current_user.withdrawable_wallet,
        task_wallet=current_user.task_wallet,
        team_wallet=current_user.team_wallet,
        withdrawn=current_user.withdrawn,
        commissions=current_user.commissions,
        today_earnings=today_earnings,

        # Totals
        total_income=total_income,
        total_paid=total_paid,

        # Referral
        referral_link=referral_link,
        total_referrals=total_referrals,

        # VIP
        vip_level=current_user.vip_level,
        vip_expires_at=current_user.vip_expires_at,
        vip_days_left=vip_days_left
    )
# ---------------- LOGOUT ----------------
@app.route("/logout")
@login_required
@active_account_required
def logout():
    logout_user()
    return redirect("/login")



#--------------FORGOT PASSWORD-------------
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form["email"]
        user = User.query.filter_by(email=email).first()

        if not user:
            return "No account found with that email."

        otp = str(random.randint(100000, 999999))

        otp_store[email] = {
            "otp": otp,
            "time": time.time()
        }

        url = "https://api.brevo.com/v3/smtp/email"

        headers = {
            "accept": "application/json",
            "api-key": os.getenv("BREVO_API_KEY"),
            "content-type": "application/json"
        }

        payload = {
            "sender": {
                "name": "SUPERNOVA EARN",
                "email": "petersongitonga02@gmail.com"
            },
            "to": [{"email": email}],
            "subject": "SUPERNOVE EARN Password Reset Code",
            "htmlContent": f"""
            <div style="font-family:Arial,sans-serif;padding:20px;">
                <h2>SUPERNOVA EARN</h2>
                <p>Hello,</p>
        
                <p>You requested to reset your password.</p>
        
                <h1 style="letter-spacing:5px;">{otp}</h1>
        
                <p>This code expires in <strong>5 minutes</strong>.</p>
        
                <p>If you didn't request this, simply ignore this email.</p>
        
                <hr>
        
                <small>© supernova earn</small>
            </div>
            """
}

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=15
            )

            print("Brevo Status:", response.status_code)
            print("Brevo Response:", response.text)

            if response.status_code in [200, 201]:
                return redirect(f"/verify-otp/{email}")
            else:
                return f"Brevo Error:<br>{response.text}"

        except Exception as e:
            return f"Error sending email: {e}"

    return render_template("forgot_password.html")

#----------------OTP VERIFICATION------------
@app.route("/verify-otp/<email>", methods=["GET", "POST"])
def verify_otp(email):

    if request.method == "POST":

        user_otp = request.form["otp"]

        data = otp_store.get(email)

        if not data:
         return render_template("otp_expired.html")

        if time.time() - data["time"] > 300:
            return render_template("otp_expired.html")

        if data["otp"] == user_otp:
            return redirect(f"/reset-password/{email}")

        return "Invalid OTP"

    return render_template("verify_otp.html", email=email)

#-------------RESET PASSWORD----------------

@app.route("/reset-password/<email>", methods=["GET", "POST"])
def reset_password(email):

    user = User.query.filter_by(email=email).first()

    if request.method == "POST":

        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        # 🔴 PASSWORD MATCH CHECK
        if new_password != confirm_password:
            return "Passwords do not match"

        user.password = generate_password_hash(new_password)
        db.session.commit()

        return redirect("/login")

    return render_template("reset_password.html", email=email)

#-----------RESEND OTP BUTTON----------
@app.route("/resend-otp/<email>")
def resend_otp(email):

    user = User.query.filter_by(email=email).first()

    if not user:
        return "User not found"

    otp = str(random.randint(100000, 999999))

    otp_store[email] = {
        "otp": otp,
        "time": time.time()
    }

    msg = Message(
        "New OTP Code",
        sender=app.config['MAIL_USERNAME'],
        recipients=[email]
    )

    msg.body = f"Your new OTP is: {otp}"

    try:
        mail.send(msg)
        print("Email sent successfully")
    except Exception as e:
        print("SMTP ERROR:", e)
        return f"SMTP ERROR: {e}"

    return redirect(f"/verify-otp/{email}")

#--------------WEBHOOK------------------
@app.route("/webhook", methods=["POST"])
def webhook():

    data = request.get_json()

    print("=" * 60)
    print("WEBHOOK RECEIVED")
    print(data)
    print("=" * 60)

    topic = data.get("topic", "")
    status = data.get("status", "").upper()
    tracking_id = data.get("tracking_id")

    print("TOPIC:", topic)
    print("STATUS:", status)
    print("TRACKING:", tracking_id)

    # ====================================================
    # WITHDRAWAL WEBHOOK (B2C SEND MONEY)
    # ====================================================
    if topic == "send_money_event":

        withdrawal = Withdrawal.query.filter_by(
            intasend_transaction_id=tracking_id
        ).first()

        print("Withdrawal found:", withdrawal)

        if not withdrawal:
            return jsonify({"status": "received"}), 200

        user = User.query.get(withdrawal.user_id)

        # ----------------------------
        # SUCCESSFUL WITHDRAWAL
        # ----------------------------
        if status in [
            "COMPLETED",
            "SUCCESSFUL",
            "PAID"
        ]:

            withdrawal.status = "Paid"
            withdrawal.processed_at = datetime.utcnow()

            # Deduct wallets
            user.main_wallet -= withdrawal.amount
            user.withdrawable_wallet -= withdrawal.amount

            # Prevent negatives
            user.main_wallet = max(user.main_wallet, 0)
            user.withdrawable_wallet = max(
                user.withdrawable_wallet,
                0
            )

            user.withdrawn += withdrawal.amount

            # Consume contribution only once
            if not user.contribution_deducted:

                required = get_required_contribution(
                    user.vip_level
                )

                user.referral_contribution_balance -= required

                user.referral_contribution_balance = max(
                    user.referral_contribution_balance,
                    0
                )

                user.contribution_deducted = True

                db.session.add(
                    ContributionHistory(
                        user_id=user.id,
                        referred_user_id=user.id,
                        amount=-required,
                        description=f"{user.vip_level} contribution used"
                    )
                )

            db.session.add(
                Transaction(
                    user_id=user.id,
                    transaction_type="withdrawal",
                    wallet="main",
                    amount=-withdrawal.amount,
                    description="Automatic Withdrawal"
                )
            )

            db.session.add(
                Notification(
                    user_id=user.id,
                    title="Withdrawal Successful",
                    message=f"KES {withdrawal.amount:.2f} has been sent to your M-Pesa."
                )
            )

        # ----------------------------
        # FAILED
        # ----------------------------
        elif status == "FAILED":

            withdrawal.status = "Failed"

            db.session.add(
                Notification(
                    user_id=user.id,
                    title="Withdrawal Failed",
                    message="Your withdrawal could not be processed."
                )
            )

        db.session.commit()

        return jsonify({"status": "received"}), 200


    invoice_id = data.get("invoice_id")
    state = data.get("state", "").upper()
    tracking_id = data.get("tracking_id")

    print("WEBHOOK TRACKING ID:", tracking_id)
    print("INVOICE:", invoice_id)
    print("STATE:", state)


    payment = Payment.query.filter_by(
        transaction_code=invoice_id
    ).first()

    print("PAYMENT FOUND:", payment)

    if payment:

        if state in ["COMPLETE", "COMPLETED", "SUCCESSFUL"]:
            
            payment.status = "approved"

            

            # =========================
            # RECHARGE PAYMENT
            # =========================
            if payment.payment_type == "recharge":

                user = User.query.get(payment.user_id)

                if not user:
                    return jsonify({"status": "received"}), 200

                # -----------------------------
                # Credit Recharge
                # -----------------------------
                user.recharge_balance += payment.amount
                user.main_wallet += payment.amount

                # ---------------------------------
                # ACTIVATE / RENEW VIP MEMBERSHIP
                # ---------------------------------

                # ---------------------------------
                # PROCESS VIP MEMBERSHIP
                # ---------------------------------

                old_vip = user.vip_level

                process_vip_recharge(user, payment.amount)

                # -----------------------------
                # Recharge Transaction
                # -----------------------------
                db.session.add(
                    Transaction(
                        user_id=user.id,
                        transaction_type="recharge",
                        wallet="main",
                        amount=payment.amount,
                        description="Wallet Recharge"
                    )
                )

                # -----------------------------
                # VIP Notification
                # -----------------------------
                if old_vip != user.vip_level:

                    db.session.add(
                        Notification(
                            user_id=user.id,
                            title="VIP Upgraded",
                            message=f"Congratulations! You have been upgraded to {user.vip_level}."
                        )
                    )

                elif (
                            old_vip == user.vip_level
                            and user.vip_started_at
                            and user.vip_started_at >= now - timedelta(seconds=5)
                        ):

                    db.session.add(
                        Notification(
                            user_id=user.id,
                            title="VIP Renewed",
                            message=f"Your {user.vip_level} membership has been renewed for another 30 days."
                        )
                    )

                # =============================
                # REFERRAL COMMISSION
                # =============================
                if user.referred_by:

                    referrer = User.query.filter_by(
                        referral_code=user.referred_by
                    ).first()

                    if referrer:

                        referral_bonus = payment.amount * 0.10

                        add_to_main_wallet(
                            referrer,
                            referral_bonus,
                            f"10% Referral Commission from {user.username}",
                            transaction_type="referral_commission"
                        )

                        referrer.commissions += referral_bonus

                        add_contribution(
                            referrer,
                            user,
                            payment.amount,
                            f"{user.username} recharged KES {payment.amount:.2f}"
                        )

                        update_withdrawal_status(referrer)

                        db.session.add(
                            Notification(
                                user_id=referrer.id,
                                title="Referral Commission",
                                message=(
                                    f"You earned KES {referral_bonus:.2f} from "
                                    f"{user.username}'s recharge."
                                )
                            )
                        )

                db.session.commit()

                print("Recharge processed successfully.")

                return jsonify({"status": "received"}), 200


        # =====================================
        # REGISTRATION PAYMENT
        # =====================================

        elif payment.payment_type == "registration":

            pending_user = PendingUser.query.filter_by(
                email=payment.email
            ).first()

            print("PAYMENT EMAIL:", payment.email)
            print("PENDING USER:", pending_user)

            if pending_user:

                existing_user = User.query.filter_by(
                    email=pending_user.email
                ).first()

                if not existing_user:

                    new_user = User(
                        username=pending_user.username,
                        email=pending_user.email,
                        phone=pending_user.phone,
                        password=pending_user.password,
                        referred_by=pending_user.referred_by,

                        # Wallets
                        main_wallet=0,
                        withdrawable_wallet=0,
                        vip_locked_amount=0,
                        recharge_balance=0,
                        task_wallet=0,
                        team_wallet=0,
                        withdrawn=0,
                        commissions=0,
                        referral_contribution_balance=0,

                        account_active=False
                    )

                    db.session.add(new_user)

                    # Generate ID
                    db.session.flush()

                    # Referral Code
                    new_user.referral_code = f"SN{new_user.id}"

                    print("USER CREATED:", new_user.username)
                    print("REFERRAL CODE:", new_user.referral_code)
                    print("REFERRED BY:", new_user.referred_by)

                db.session.delete(pending_user)

                db.session.commit()

                return jsonify({"status": "received"}), 200
             
        elif state == "FAILED":

                payment.status = "failed"

        elif state in ["PENDING", "PROCESSING"]:

            payment.status = state.lower()

        db.session.commit()

        print("UPDATED STATUS TO:", payment.status)

        return jsonify({"status": "received"}), 200


#--------------PENDING PAYMENT/ CHECK PAYMENT--------------------
@app.route("/check-payment/<invoice_id>")
def check_payment(invoice_id):

    print("CHECKING:", invoice_id)

    payment = Payment.query.filter_by(
        transaction_code=invoice_id
    ).first()

    if not payment:
        print("PAYMENT NOT FOUND")
        return jsonify({"status": "not_found"})

    print("CURRENT STATUS:", payment.status)

    return jsonify({
        "status": payment.status
    })
#========================recharge route==================
@app.route("/recharge", methods=["GET", "POST"])
@login_required
@active_account_required
def recharge():

    if request.method == "POST":

        phone = request.form["phone"].strip()
        amount = float(request.form["amount"])

        if phone.startswith("0"):
            phone = "254" + phone[1:]

        try:

            response = service.collect.mpesa_stk_push(
                phone_number=phone,
                amount=amount,
                narrative="Wallet Recharge"
            )
            print("PHONE:", phone)
            print("AMOUNT:", amount)
            print("INTASEND RESPONSE:", response)
            invoice_id = response["invoice"]["invoice_id"]

            payment = Payment(
                phone=phone,
                transaction_code=invoice_id,
                amount=amount,
                status="pending",
                payment_type="recharge",
                user_id=current_user.id
            )

            db.session.add(payment)
            db.session.commit()

            return render_template(
                "payment_pending.html",
                invoice_id=invoice_id,
                payment_type="recharge"
            )

        except Exception as e:
            return f"Recharge failed: {e}"

    return render_template("recharge.html")

#-----------RENEW MEMBERSHIP---------------
@app.route("/renew-membership", methods=["POST"])
@login_required
@active_account_required
def renew_membership():

    if not current_user.vip_level:

        flash("You don't have an active VIP membership.", "danger")
        return redirect(url_for("vip"))

    now = datetime.utcnow()

    # ---------------------------------
    # Renewal window
    # ---------------------------------

    if current_user.vip_expires_at:

        days_left = (
            current_user.vip_expires_at - now
        ).days

        if days_left > 2:

            flash(
                "Membership can only be renewed during the last 2 days before expiry.",
                "warning"
            )

            return redirect(url_for("vip"))

    renewal_cost = VIP_PLANS[
        current_user.vip_level
    ]["price"]

    remaining = renewal_cost

    # ---------------------------------
    # Use Task Wallet FIRST
    # ---------------------------------

    task_used = min(
        current_user.task_wallet,
        remaining
    )

    current_user.task_wallet -= task_used

    remaining -= task_used

    # ---------------------------------
    # Use Main Wallet SECOND
    # ---------------------------------

    if remaining > 0:

        if current_user.main_wallet < remaining:

            flash(
                "Insufficient balance to renew your membership.",
                "danger"
            )

            return redirect(url_for("vip"))

        current_user.main_wallet -= remaining

    # ---------------------------------
    # Extend membership
    # ---------------------------------

    if current_user.vip_expires_at > now:

        current_user.vip_started_at = current_user.vip_expires_at

        current_user.vip_expires_at += timedelta(days=30)

    else:

        current_user.vip_started_at = now

        current_user.vip_expires_at = now + timedelta(days=30)

    current_user.contribution_deducted = False

    # ---------------------------------
    # Membership History
    # ---------------------------------

    db.session.add(

        MembershipHistory(

            user_id=current_user.id,

            vip_level=current_user.vip_level,

            contribution_used=0,

            withdrawal_unlocked=False

        )

    )

    # ---------------------------------
    # Transaction
    # ---------------------------------

    db.session.add(

        Transaction(

            user_id=current_user.id,

            transaction_type="membership_renewal",

            wallet="task/main",

            amount=-renewal_cost,

            description=f"{current_user.vip_level} Membership Renewal"

        )

    )

    # ---------------------------------
    # Notification
    # ---------------------------------

    db.session.add(

        Notification(

            user_id=current_user.id,

            title="Membership Renewed",

            message=f"Your {current_user.vip_level} membership has been renewed successfully."

        )

    )

    db.session.commit()

    flash(
        "Membership renewed successfully!",
        "success"
    )

    return redirect(url_for("vip"))
#--------------debugging-------------------------
@app.route("/debug-pending")
def debug_pending():

    pending_users = PendingUser.query.all()

    output = ""

    for user in pending_users:
        output += f"""
        ID: {user.id}<br>
        Username: {user.username}<br>
        Email: {user.email}<br>
        Phone: {user.phone}<br><hr>
        """

    return output

#-----------------SEE PAYMENTS-----------------------------
@app.route("/payments")
def payments():
    payments = Payment.query.all()

    html = ""

    for p in payments:
        html += f"""
        <p>
        {p.id} |
        {p.email} |
        {p.phone} |
        {p.transaction_code} |
        {p.status}
        </p>
        """

    return html


#---------------CHECKING IF DATA IS SAVED IN DB-----------------

@app.route("/db-test")
def db_test():
    return f"""
    Users: {User.query.count()}<br>
    Pending Users: {PendingUser.query.count()}<br>
    Payments: {Payment.query.count()}
    """
@app.route("/db-url")
def db_url():
    return app.config["SQLALCHEMY_DATABASE_URI"]

#-======================================================
@app.route("/mail-test")
def mail_test():
    return {
        "server": app.config["MAIL_SERVER"],
        "port": app.config["MAIL_PORT"],
        "username": app.config["MAIL_USERNAME"],
        "password_set": bool(app.config["MAIL_PASSWORD"]),

    
    } 

#====================================================
import smtplib

@app.route("/smtp-test")
def smtp_test():
    try:
        server = smtplib.SMTP_SSL(
            "smtp-relay.brevo.com",
            465,
            timeout=10
        )
        server.login(
            app.config["MAIL_USERNAME"],
            app.config["MAIL_PASSWORD"]
        )
        server.quit()
        return "SMTP LOGIN SUCCESS"

    except Exception as e:
        return str(e)


#============================profile=========================
@app.route("/profile")
@login_required
@active_account_required
def profile():

    total_referrals = User.query.filter_by(
        referred_by=current_user.referral_code
    ).count()

    total_income = (
        current_user.main_wallet +
        current_user.task_wallet +
        current_user.team_wallet
    )

    active_tasks = 0

    return render_template(
        "profile.html",
        user=current_user,
        total_income=total_income,
        total_referrals=total_referrals,
        active_tasks=active_tasks,
        main_wallet=current_user.main_wallet,
        task_wallet=current_user.task_wallet,
        team_wallet=current_user.team_wallet,
        withdrawn=current_user.withdrawn
    )

#============================================================
@app.route("/edit-profile", methods=["GET", "POST"])
@login_required
@active_account_required
def edit_profile():

    if request.method == "POST":

        current_user.username = request.form["username"]
        current_user.phone = request.form["phone"]

        db.session.commit()

        return redirect("/profile")

    return render_template("edit_profile.html", user=current_user)    

#===================notification route=====================
@app.route("/notifications")
@login_required
@active_account_required
def notifications():

    notes = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Notification.created_at.desc()
    ).all()

    return render_template(
        "notifications.html",
        notes=notes
    )

#============WALLETS/vip plans HELPERS FUNCTIONS=========
def add_to_main_wallet(user, amount, description, transaction_type="deposit"):

    user.main_wallet += amount

    transaction = Transaction(
        user_id=user.id,
        transaction_type=transaction_type,
        wallet="main",
        amount=amount,
        description=description
    )

    db.session.add(transaction)

def add_to_task_wallet(user, amount, description):

    user.task_wallet += amount

    user.main_wallet += amount

    user.withdrawable_wallet += amount

    transaction = Transaction(
        user_id=user.id,
        transaction_type="task_reward",
        wallet="task",
        amount=amount,
        description=description
    )

    db.session.add(transaction)

def add_to_team_wallet(user, amount, description):

    user.team_wallet += amount

    transaction = Transaction(
        user_id=user.id,
        transaction_type="team_bonus",
        wallet="team",
        amount=amount,
        description=description
    )

    db.session.add(transaction)

def get_daily_task_limit(vip_level):

    limits = {
        "Bronze": 1,
        "Silver": 3,
        "Gold": 4,
        "Platinum": 5,
        "Diamond": 5
    }

    return limits.get(vip_level, 0)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if not current_user.is_authenticated:
            abort(401)

        if not current_user.is_admin:
            abort(403)

        return f(*args, **kwargs)

    return decorated_function


def get_required_contribution(vip):

    requirements = {
        "Bronze":10,
        "Silver": 1500,
        "Gold": 3000,
        "Platinum": 7500,
        "Diamond": 15000
    }

    return requirements.get(vip, 0)

def add_contribution(user, referred_user, amount, description):

    user.referral_contribution_balance += amount

    db.session.add(
        ContributionHistory(
            user_id=user.id,
            referred_user_id=referred_user.id,
            amount=amount,
            description=description
        )
    )

from datetime import datetime

def can_withdraw(user):

    # Account inactive
    if not user.account_active:
        return False, "Your account is inactive."

    # VIP expired
    if not user.vip_expires_at:
        return False, "You do not have an active membership."

    if datetime.utcnow() > user.vip_expires_at:
        return False, "Your VIP membership has expired."

    # Contribution requirement
    required = get_required_contribution(user.vip_level)

    if user.referral_contribution_balance < required:
        remaining = required - user.referral_contribution_balance

        return (
            False,
            f"You need KES {remaining:.2f} more contribution to unlock withdrawals."
        )
    
        # Withdrawable balance
    minimum = get_minimum_withdrawal(user.vip_level)

    if user.withdrawable_wallet < minimum:
        return (
            False,
            f"You need at least KES {minimum:.2f} in your withdrawable wallet."
        )

    return True, "Withdrawal unlocked."



def update_withdrawal_status(user):

    required = get_required_contribution(user.vip_level)

    if user.referral_contribution_balance >= required:
        user.withdrawal_unlocked = True
    else:
        user.withdrawal_unlocked = False



def deduct_membership_contribution(user):

    required = get_required_contribution(user.vip_level)

    if user.referral_contribution_balance < required:
        return False

    user.referral_contribution_balance -= required

    db.session.add(
        MembershipHistory(
            user_id=user.id,
            vip_level=user.vip_level,
            contribution_used=required,
            withdrawal_unlocked=False
        )
    )

    return True

def get_minimum_withdrawal(vip_level):
    minimums = {
        "Bronze": 5,
        "Silver": 1000,
        "Gold": 2000,
        "Platinum": 5000,
        "Diamond": 10000
    }

    return minimums.get(vip_level, 500)

from datetime import datetime, timedelta

RENEWAL_WINDOW_DAYS = 2


def get_minimum_recharge(vip_level):

    recharge_requirements = {
        "Bronze": 10,
        "Silver": 500,
        "Gold": 1000,
        "Platinum": 2500,
        "Diamond": 5000,
        
    }

    return recharge_requirements.get(vip_level, 0)



def update_vip_lock(user):

    required_lock = get_minimum_recharge(user.vip_level)

    # Lock only the recharge money required by the VIP
    user.vip_locked_amount = min(
        required_lock,
        user.recharge_balance
    )

    # Extra recharge beyond the lock
    extra_recharge = max(
        user.recharge_balance - user.vip_locked_amount,
        0
    )

    # Task earnings are always withdrawable
    user.withdrawable_wallet = (
        extra_recharge +
        user.task_wallet
    )




def get_vip_price(vip_level):
    plan = VIP_PLANS.get(vip_level)
    return plan["price"] if plan else 0


def can_renew(user):
    """
    User can renew only if:
    - Membership already expired
    OR
    - Remaining days <= 2
    """

    if not user.vip_expires_at:
        return True

    remaining = user.vip_expires_at - datetime.utcnow()

    return remaining.days <= RENEWAL_WINDOW_DAYS


def renew_membership(user):
    """
    Adds 30 days without changing VIP level.
    """

    now = datetime.utcnow()

    if not user.vip_expires_at or user.vip_expires_at < now:

        user.vip_started_at = now
        user.vip_expires_at = now + timedelta(days=30)

    else:

        user.vip_started_at = user.vip_expires_at
        user.vip_expires_at += timedelta(days=30)

    user.contribution_deducted = False


def upgrade_membership(user, new_level):
    """
    Changes VIP level immediately.
    """

    user.vip_level = new_level

    now = datetime.utcnow()

    if not user.vip_started_at:
        user.vip_started_at = now

    if not user.vip_expires_at or user.vip_expires_at < now:
        user.vip_expires_at = now + timedelta(days=30)

def get_renewal_price(vip_level):

    if vip_level not in VIP_PLANS:
        return 0

    return VIP_PLANS[vip_level]["price"]
#----------upgrade order------------------

def get_next_vip(current_level):
    """
    Returns the next VIP level.
    Example:
    Bronze -> Silver
    Silver -> Gold
    """

    try:
        index = VIP_ORDER.index(current_level)

        if index < len(VIP_ORDER) - 1:
            return VIP_ORDER[index + 1]

    except ValueError:
        return None

    return None



def get_upgrade_cost(current_level, new_level):

    current_price = get_vip_price(current_level)
    new_price = get_vip_price(new_level)

    return max(new_price - current_price, 0)


def can_upgrade(user):
    """
    Returns True if there is a higher VIP level.
    """

    return get_next_vip(user.vip_level) is not None
def can_afford_upgrade(user):

    next_vip = get_next_vip(user.vip_level)

    if not next_vip:
        return False

    cost = get_upgrade_cost(
        user.vip_level,
        next_vip
    )

    return user.main_wallet >= cost

def get_locked_capital(user):

    if user.vip_level == "Free":
        return 0

    return VIP_PLANS[user.vip_level]["price"]

def get_withdrawable_balance(user):
    """
    Calculates the user's available withdrawal amount.
    """

    locked_capital = get_locked_capital(user)

    # Recharge money that can be withdrawn
    recharge_available = max(
        user.recharge_balance - locked_capital,
        0
    )

    # Task earnings
    task_available = 0

    if can_withdraw(user)[0]:
        task_available = user.task_wallet

    return recharge_available + task_available

def get_upgrade_amount(user, new_level):

    if new_level == user.vip_level:
        return 0

    return get_upgrade_cost(
        user.vip_level,
        new_level
    )

from datetime import datetime, timedelta

def process_vip_recharge(user, amount):

    now = datetime.utcnow()

    # -----------------------------------------
    # FIRST VIP ACTIVATION ONLY
    # -----------------------------------------
    if not user.vip_level:

        if amount >= 5000:
            user.vip_level = "Diamond"

        elif amount >= 2500:
            user.vip_level = "Platinum"

        elif amount >= 1000:
            user.vip_level = "Gold"

        elif amount >= 500:
            user.vip_level = "Silver"

        elif amount >= 200:
            user.vip_level = "Bronze"

        else:
            return

        # Start first membership
        user.account_active = True
        user.vip_started_at = now
        user.vip_expires_at = now + timedelta(days=30)

        user.tasks_completed = 0
        user.last_task_date = None
        user.contribution_deducted = False

    # -----------------------------------------
    # Existing VIP
    # -----------------------------------------
    else:

        # VIP is still active
        if user.vip_expires_at and user.vip_expires_at > now:

            # Recharge only.
            # No renewal.
            # No upgrade.
            pass

        # VIP expired
        else:

            # Recharge only.
            # User must click Renew.
            user.account_active = False

    # Update locked/withdrawable wallets
    update_vip_lock(user)

#------------------VIP TASK ROUTE---------------------
@app.route("/vip")
@login_required
@active_account_required
def vip():

    plans = []

    for plan_name in VIP_ORDER:

        plans.append({

            "name": plan_name,
            "price": VIP_PLANS[plan_name]["price"],
            "daily_income": VIP_PLANS[plan_name]["reward"],
            "tasks": VIP_PLANS[plan_name]["tasks"]

        })

    vip_days_left = None

    if current_user.vip_expires_at:

        vip_days_left = (
            current_user.vip_expires_at - datetime.utcnow()
        ).days

    return render_template(

        "vip.html",

        plans=plans,

        current_vip=current_user.vip_level,

        VIP_ORDER=VIP_ORDER,

        VIP_PLANS=VIP_PLANS,

        get_upgrade_cost=get_upgrade_cost,

        can_upgrade=can_upgrade,

        current_user=current_user,

        vip_days_left=vip_days_left

    )
#--------------VIP UPGRADE ROUTE---------------
@app.route("/upgrade-vip/<plan>", methods=["POST"])
@login_required
@active_account_required
def upgrade_vip(plan):

    # ----------------------------
    # VIP exists?
    # ----------------------------
    if plan not in VIP_PLANS:

        flash("Invalid VIP plan.", "danger")
        return redirect(url_for("vip"))

    # ----------------------------
    # Cannot downgrade
    # ----------------------------
    if current_user.vip_level:

        current_index = VIP_ORDER.index(current_user.vip_level)
        new_index = VIP_ORDER.index(plan)

        if new_index <= current_index:

            flash("You can only upgrade to a higher VIP.", "warning")
            return redirect(url_for("vip"))

    # ----------------------------
    # Calculate cost
    # ----------------------------
    if current_user.vip_level:

        amount_required = get_upgrade_cost(
            current_user.vip_level,
            plan
        )

    else:

        amount_required = VIP_PLANS[plan]["price"]

    # ----------------------------
    # Main wallet ONLY
    # ----------------------------
    if current_user.main_wallet < amount_required:

        flash(
            f"Insufficient Main Wallet balance. You need KES {amount_required:.2f} to upgrade to {plan}.",
            "danger"
        )

        return redirect(url_for("vip"))

    # ----------------------------
    # Task earnings protection
    # ----------------------------
    earned_from_tasks = current_user.task_wallet

    if not can_withdraw(current_user)[0]:

        usable_main = current_user.main_wallet - earned_from_tasks

        if usable_main < amount_required:

            flash(
                "Task earnings cannot be used for VIP upgrades until you meet the withdrawal requirements.",
                "warning"
            )

            return redirect(url_for("vip"))

    # ----------------------------
    # Deduct Main Wallet
    # ----------------------------
    current_user.main_wallet -= amount_required

    # ----------------------------
    # Change VIP
    # ----------------------------
    current_user.vip_level = plan

    now = datetime.utcnow()

    # Preserve remaining days
    if current_user.vip_expires_at and current_user.vip_expires_at > now:

        remaining = current_user.vip_expires_at - now

        current_user.vip_started_at = now
        current_user.vip_expires_at = now + remaining

    else:

        current_user.vip_started_at = now
        current_user.vip_expires_at = now + timedelta(days=30)

    # Reset contribution flag
    current_user.contribution_deducted = False

    # ----------------------------
    # Membership History
    # ----------------------------
    db.session.add(

        MembershipHistory(

            user_id=current_user.id,

            vip_level=plan,

            contribution_used=0,

            withdrawal_unlocked=False

        )

    )

    # ----------------------------
    # Transaction
    # ----------------------------
    db.session.add(

        Transaction(

            user_id=current_user.id,

            transaction_type="vip_upgrade",

            wallet="main",

            amount=-amount_required,

            description=f"VIP upgraded to {plan}"

        )

    )

    # ----------------------------
    # Notification
    # ----------------------------
    db.session.add(

        Notification(

            user_id=current_user.id,

            title="VIP Upgraded",

            message=f"You successfully upgraded to {plan}."

        )

    )

    db.session.commit()

    flash(
        f"Congratulations! You are now a {plan} member.",
        "success"
    )

    return redirect(url_for("vip"))
#---------------TASK ROUTE---------------------
from datetime import date
from models import Task, UserTask

@app.route("/tasks")
@login_required
@active_account_required
def tasks():

    # Get today's tasks for the current VIP
    tasks = Task.query.filter_by(
        vip_level=current_user.vip_level,
        active=True
    ).all()

    # VIP plan details
    plan = VIP_PLANS[current_user.vip_level]
    daily_limit = int(plan["tasks"])
    daily_reward = int(plan["tasks"] * plan["reward"])

    # Tasks completed today
    completed_tasks = UserTask.query.filter(
        UserTask.user_id == current_user.id,
        db.func.date(UserTask.completed_at) == date.today()
    ).all()

    completed_ids = [t.task_id for t in completed_tasks]

    completed_today = len(completed_ids)

    return render_template(
        "tasks.html",
        tasks=tasks,
        completed_ids=completed_ids,
        completed_today=completed_today,
        daily_limit=daily_limit,
        daily_reward=daily_reward
    )
#-----------TEAM ROUTE----------------
@app.route("/team")
@login_required
@active_account_required
def team():

    referrals = User.query.filter_by(
        referred_by=current_user.referral_code
    ).all()

    total_referrals = len(referrals)

    total_team_recharge = 0

    for member in referrals:

        recharge = db.session.query(
            db.func.sum(Payment.amount)
        ).filter(
            Payment.user_id == member.id,
            Payment.payment_type == "recharge",
            Payment.status == "approved"
        ).scalar() or 0

        member.total_recharge = recharge
        total_team_recharge += recharge

    return render_template(
        "team.html",
        referrals=referrals,
        total_referrals=total_referrals,
        total_team_recharge=total_team_recharge,
        commissions=current_user.commissions
    )

#--------------ADMNIN TASK ROUTE----------------
@app.route("/admin/tasks", methods=["GET", "POST"])
@login_required
@active_account_required
def admin_tasks():

    # Replace this with your own admin check later
    if current_user.email != "petersongitonga02@gmail.com":
        return "Access Denied"

    if request.method == "POST":

        task = Task(
            title=request.form["title"],
            description=request.form["description"],
            reward=float(request.form["reward"]),
            vip_level=request.form["vip_level"],
            url=request.form["url"],
            active=True
        )

        db.session.add(task)
        db.session.commit()

        return redirect("/admin/tasks")

    tasks = Task.query.order_by(Task.id.desc()).all()

    return render_template(
        "admin_tasks.html",
        tasks=tasks
    )

#------------delete task admin---------------
@app.route("/admin/delete-task/<int:task_id>", methods=["POST"])
@login_required
@admin_required
def delete_task(task_id):

    task = Task.query.get_or_404(task_id)

    # Delete task completions first
    UserTask.query.filter_by(task_id=task.id).delete()

    # Delete task sessions
    TaskSession.query.filter_by(task_id=task.id).delete()

    db.session.delete(task)
    db.session.commit()

    flash("Task deleted successfully.")

    return redirect("/admin/tasks")
#-----------------------dmin edit task------------------
@app.route("/admin/edit-task/<int:task_id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_task(task_id):

    task = Task.query.get_or_404(task_id)

    if request.method == "POST":

        task.title = request.form.get("title")
        task.description = request.form.get("description")
        task.reward = float(request.form.get("reward"))
        task.vip_level = request.form.get("vip_level")
        task.url = request.form.get("url")

        task.active = "active" in request.form

        db.session.commit()

        flash("Task updated successfully.")

        return redirect("/admin/tasks")

    return render_template(
        "edit_task.html",
        task=task
    )
#--------------REWARD/claim ROUTE------------------
from datetime import datetime, date
from flask import jsonify, redirect

@app.route("/claim-task/<int:task_id>", methods=["POST"])
@login_required
@active_account_required
def claim_task(task_id):

    task = Task.query.get_or_404(task_id)
    token = request.form.get("session_token")

    # Task must be active
    if not task.active:
        return jsonify({
            "success": False,
            "message": "Task is inactive."
        }), 400

    # VIP check
    if task.vip_level != current_user.vip_level:
        return jsonify({
            "success": False,
            "message": "This task is not available for your VIP."
        }), 403

    # Already completed today?
    completed = UserTask.query.filter(
        UserTask.user_id == current_user.id,
        UserTask.task_id == task.id,
        db.func.date(UserTask.completed_at) == date.today()
    ).first()

    if completed:
        return jsonify({
            "success": False,
            "message": "You already completed this task today."
        }), 400

    # Daily task limit
    completed_today = UserTask.query.filter(
        UserTask.user_id == current_user.id,
        db.func.date(UserTask.completed_at) == date.today()
    ).count()

    daily_limit = get_daily_task_limit(current_user.vip_level)

    print("VIP:", current_user.vip_level)
    print("Completed today:", completed_today)
    print("Daily limit:", daily_limit)

    if completed_today >= daily_limit:
        return jsonify({
            "success": False,
            "message": "You have reached today's task limit."
        }), 400

    print("===== CLAIM REQUEST =====")
    print("Task ID:", task.id)
    print("User ID:", current_user.id)
    print("Received token:", token)
    # Find task session
    session = TaskSession.query.filter_by(
        user_id=current_user.id,
        task_id=task.id,
        session_token=token,
        completed=False
    ).first()

    print("Session found:", session)

    if not session:
        return jsonify({
            "success": False,
            "message": "Task session not found."
        }), 400

    # Reward already claimed?
    if session.completed:
        return jsonify({
            "success": False,
            "message": "Reward already claimed."
        }), 400

    # Server-side watch verification
    if session.watched_seconds < 25:
        return jsonify({
            "success": False,
            "message": "Please finish watching the video."
        }), 400

    # Extra protection against fake requests
    elapsed = (datetime.utcnow() - session.started_at).total_seconds()

    print("Elapsed:", elapsed)

    if elapsed < 25:
        return jsonify({
            "success": False,
            "message": "Please finish watching the video."
        }), 400

    # Mark session completed
    session.completed = True

    # Credit Task Wallet
    add_to_task_wallet(
        current_user,
        task.reward,
        task.title
    )

    # Increase completed tasks counter
    current_user.tasks_completed += 1

    # Save completion
    db.session.add(
        UserTask(
            user_id=current_user.id,
            task_id=task.id
        )
    )

    # Notification
    db.session.add(
        Notification(
            user_id=current_user.id,
            title="Task Completed",
            message=f"You earned KES {task.reward:.2f}."
        )
    )

    # Delete the session so it cannot be reused
    db.session.delete(session)

    db.session.commit()

    return redirect("/tasks")

#------------ADMIN  ROUTE---------------------
@app.route("/admin")
@login_required
@admin_required
def admin():

    total_users = User.query.count()

    pending_recharges = Payment.query.filter_by(
        status="pending",
        payment_type="recharge"
    ).count()

    pending_withdrawals = Transaction.query.filter_by(
        transaction_type="withdrawal",
        status="Pending"
    ).count()

    vip_members = User.query.filter(
        User.vip_level != "Bronze"
    ).count()

    total_deposits = db.session.query(
        db.func.sum(Payment.amount)
    ).filter(
        Payment.status == "approved",
        Payment.payment_type == "recharge"
    ).scalar() or 0

    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        pending_recharges=pending_recharges,
        pending_withdrawals=pending_withdrawals,
        vip_members=vip_members,
        total_deposits=total_deposits
    )

#--------------ADMIN USERS ROUTE------------------
@app.route("/admin/users")
@login_required
@admin_required
def admin_users():

    users = User.query.order_by(User.joined_at.desc()).all()

    return render_template(
        "admin/users.html",
        users=users
    )


#--------------------ADMIN_USER -----------------
@app.route("/admin/toggle-user/<int:user_id>")
@login_required
@admin_required
def toggle_user(user_id):

    user = User.query.get_or_404(user_id)

    # Don't allow admin to suspend themselves
    if user.id == current_user.id:
        flash("You cannot suspend your own account.")
        return redirect("/admin/users")

    user.account_active = not user.account_active

    db.session.commit()

    if user.account_active:
        flash(f"{user.username} has been activated.")
    else:
        flash(f"{user.username} has been suspended.")

    return redirect("/admin/users")

#-------------USERS DETAIL ROUTE-----------------
@app.route("/admin/user/<int:user_id>")
@login_required
@admin_required
def admin_user(user_id):

    user = User.query.get_or_404(user_id)

    return render_template(
        "admin/user.html",
        user=user
    )

#---------------SUSPEND ROUTE--------------------
@app.route("/admin/suspend/<int:user_id>")
@login_required
@admin_required
def suspend_user(user_id):

    user = User.query.get_or_404(user_id)

    user.account_active = False

    db.session.commit()

    return redirect("/admin/users")
#--------------ACTIVATE ROUTE-------------------
@app.route("/admin/activate/<int:user_id>")
@login_required
@admin_required
def activate_user(user_id):

    user = User.query.get_or_404(user_id)

    user.account_active = True

    db.session.commit()

    return redirect("/admin/users")

#--------------CHANGE VIP FROM ADMIN------------
@app.route("/admin/change-vip/<int:user_id>/<vip>")
@login_required
@admin_required
def change_vip(user_id, vip):

    user = User.query.get_or_404(user_id)

    user.vip_level = vip

    db.session.commit()

    return redirect(f"/admin/user/{user.id}")
#--------------EDIT WALLETS----------------
@app.route("/admin/add-main-wallet/<int:user_id>/<float:amount>")
@login_required
@admin_required
def add_wallet(user_id, amount):

    user = User.query.get_or_404(user_id)

    user.main_wallet += amount

    db.session.commit()

    return redirect(f"/admin/user/{user.id}")

#---------------MANAGE WALLETS-----------------------
@app.route("/admin/wallet/<int:user_id>", methods=["GET", "POST"])
@login_required
@admin_required
def admin_wallet(user_id):

    user = User.query.get_or_404(user_id)

    if request.method == "POST":

        wallet = request.form["wallet"]

        amount = float(request.form["amount"])

        reason = request.form["reason"]

        if wallet == "main":
            user.main_wallet += amount

        elif wallet == "task":
            user.task_wallet += amount

        elif wallet == "team":
            user.team_wallet += amount

        db.session.add(
            Transaction(
                user_id=user.id,
                transaction_type="admin_adjustment",
                wallet=wallet,
                amount=amount,
                description=reason,
                status="Completed"
            )
        )

        db.session.commit()

        return redirect(f"/admin/user/{user.id}")

    return render_template(
        "admin/wallet.html",
        user=user
    )

#-------------PENDING RECHARGES------------------
@app.route("/admin/recharges")
@login_required
@admin_required
def admin_recharges():

    payments = Payment.query.filter_by(
        payment_type="recharge",
        status="pending"
    ).all()

    return render_template(
        "admin/recharges.html",
        payments=payments
    )

#---------------APPROVE RECHARGES---------------
from datetime import datetime, timedelta
@app.route("/admin/approve-recharge/<int:payment_id>")
@login_required
@admin_required
def approve_recharge(payment_id):

    now = datetime.utcnow()

    user.vip_started_at = now
    user.vip_expires_at = now + timedelta(days=30)

    user.tasks_completed = 0
    user.last_task_date = None

    payment = Payment.query.get_or_404(payment_id)

    user = User.query.get(payment.user_id)

    if payment.status != "pending":
        return redirect("/admin/recharges")

    payment.status = "approved"

    user.main_wallet += payment.amount


    # PAY REFERRAL COMMISSION
    if user.referred_by:

        referrer = User.query.filter_by(
            referral_code=user.referred_by
        ).first()

        if referrer:

            commission = payment.amount * 0.10

            referrer.team_wallet += commission

            referrer.commissions += commission

            db.session.add(
                Transaction(
                    user_id=referrer.id,
                    transaction_type="referral_commission",
                    amount=commission,
                    wallet="team",
                    description=f"10% commission from {user.username}"
                )
            )

            db.session.add(
                Notification(
                    user_id=referrer.id,
                    title="Referral Bonus",
                    message=f"You earned KES {commission:.2f} because {user.username} recharged."
                )
            )

    # Upgrade VIP
    if payment.amount >= 5000:
        user.vip_level = "Diamond"

    elif payment.amount >= 2500:
        user.vip_level = "Platinum"

    elif payment.amount >= 1000:
        user.vip_level = "Gold"

    elif payment.amount >= 500:
        user.vip_level = "Silver"

    elif payment.amount >= 200:
        user.vip_level = "Bronze"

    db.session.add(
    Notification(
        user_id=user.id,
        title="Recharge Approved",
        message=f"Your recharge of KES {payment.amount:.2f} has been approved."
        )
    )

    db.session.add(
    Transaction(
        user_id=user.id,
        transaction_type="deposit",
        amount=payment.amount,
        wallet="main",
        description="Recharge Approved"
        )
    )

    db.session.commit()

    return redirect("/admin/recharges")

#------------REJECT RECHARGES-----------------
@app.route("/admin/reject-recharge/<int:payment_id>")
@login_required
@admin_required
def reject_recharge(payment_id):

    payment = Payment.query.get_or_404(payment_id)

    payment.status = "rejected"

    db.session.commit()

    return redirect("/admin/recharges")
  #-------------RECHARGE HISTORY------------------
@app.route("/recharge-history")
@login_required
@active_account_required
def recharge_history():

    recharges = Payment.query.filter_by(
        user_id=current_user.id,
        payment_type="recharge"
    ).order_by(
        Payment.id.desc()
    ).all()

    return render_template(
        "recharge_history.html",
        recharges=recharges
    )

#----------------START TASK ROUTE--------------------
from datetime import datetime
import re

@app.route("/start-task/<int:task_id>")
@login_required
@active_account_required
def start_task(task_id):

    task = Task.query.get_or_404(task_id)

    # Task must be active
    if not task.active:
        return redirect("/tasks")

    # VIP restriction
    if task.vip_level != current_user.vip_level:
        return redirect("/tasks")

    # Remove any unfinished session
    TaskSession.query.filter_by(
        user_id=current_user.id,
        task_id=task.id
    ).delete()

    # Create new session
    import secrets

    session = TaskSession(
        user_id=current_user.id,
        task_id=task.id,
        started_at=datetime.utcnow(),
        watched_seconds=0,
        completed=False,
        session_token=secrets.token_hex(32)
    )
    db.session.add(session)
    db.session.commit()

    print("SESSION CREATED")
    print(session.user_id)
    print(session.task_id)
    print(session.completed)

    # Extract YouTube video ID
    if not task.url:
        return "No video URL found.", 400

    match = re.search(
        r"(?:youtube\.com/(?:embed/|watch\?v=)|youtu\.be/)([^?&/]+)",
        task.url
    )

    if not match:
        return "Invalid YouTube URL.", 400

    video_id = match.group(1)

    return render_template(
        "start_task.html",
        task=task,
        video_id=video_id,
        session_token=session.session_token
    )

#---------------TASK ALERT-------------------
@app.route("/task-access")
@login_required
@active_account_required
def task_access():

    # Free/Bronze users must have at least KES 200 in Main Wallet
    if current_user.vip_level == "Bronze":

        if current_user.main_wallet < 10:
            return render_template("task_alert.html")

    return redirect("/tasks")
#-----------------PROGRESS ROUTE------------------
from flask import request, jsonify
from datetime import datetime

@app.route("/update-task-progress", methods=["POST"])
@login_required
@active_account_required
def update_task_progress():

    data = request.get_json()

    task_id = int(data.get("task_id"))
    watched = int(data.get("watched",0))
    token = data.get("token")

    session = TaskSession.query.filter_by(

        user_id=current_user.id,
        task_id=task_id,
        session_token=token,
        completed=False

    ).first()

    if not session:
        return jsonify(success=False), 404

    # Never allow more than 25 seconds
    watched = min(watched, 25)

    # User cannot report more time than has actually passed
    elapsed = int((datetime.utcnow() - session.started_at).total_seconds())

    if watched > elapsed:
        watched = elapsed

    # Only increase progress
    if watched > session.watched_seconds:

        session.watched_seconds = watched

        print(
        "Progress:",
        watched,
        "Stored:",
        session.watched_seconds
             )
        
        db.session.commit()

    return jsonify(
        success=True,
        watched=session.watched_seconds
    )

#-------------Progress system page---------------
@app.route("/progress")
@login_required
@active_account_required
def progress():

    required = get_required_contribution(current_user.vip_level)

    current = current_user.referral_contribution_balance

    remaining = max(required - current, 0)

    percentage = min(
        (current_user.referral_contribution_balance /
        get_required_contribution(current_user.vip_level)) * 100,
        100
    )

    history = ContributionHistory.query.filter_by(
        user_id=current_user.id
    ).order_by(
        ContributionHistory.created_at.desc()
    ).all()

    membership_history = MembershipHistory.query.filter_by(
    user_id=current_user.id
    ).order_by(
        MembershipHistory.renewed_at.desc()
    ).all()

    return render_template(
        "progress.html",
        required=required,
        current=current,
        remaining=remaining,
        percentage=percentage,
        history=history,
        membership_history=membership_history
    )

#--------------Withdraw Route------------------
from uuid import uuid4

@app.route("/withdraw", methods=["GET", "POST"])
@login_required
@active_account_required
def withdraw():

    if request.method == "GET":

        pending_withdrawal = Withdrawal.query.filter_by(
            user_id=current_user.id,
            status="Pending"
        ).first()

        withdrawals = Withdrawal.query.filter_by(
            user_id=current_user.id
        ).order_by(
            Withdrawal.created_at.desc()
        ).all()

        required_contribution = get_required_contribution(
            current_user.vip_level
        )

        minimum_withdrawal = get_minimum_withdrawal(
            current_user.vip_level
        )

        return render_template(
            "withdraw.html",
            pending_withdrawal=pending_withdrawal,
            withdrawals=withdrawals,
            required_contribution=required_contribution,
            minimum_withdrawal=minimum_withdrawal,
            can_withdraw=(
                current_user.account_active
                and current_user.withdrawable_wallet >= minimum_withdrawal
                and current_user.referral_contribution_balance >= required_contribution
                and pending_withdrawal is None
            )
        )

    amount = float(request.form["amount"])
    phone = request.form["phone"]

    # ----------------------------
    # Eligibility
    # ----------------------------
    allowed, message = can_withdraw(current_user)

    if not allowed:
        flash(message, "danger")
        return redirect("/withdraw")

    # ----------------------------
    # Minimum withdrawal
    # ----------------------------
    minimum = get_minimum_withdrawal(current_user.vip_level)

    if amount < minimum:
        flash(
            f"Minimum withdrawal for {current_user.vip_level} is KES {minimum}.",
            "danger"
        )
        return redirect("/withdraw")

    # ----------------------------
    # Withdrawable balance
    # ----------------------------
    if amount > current_user.withdrawable_wallet:

        flash(
            "Insufficient withdrawable balance.",
            "danger"
        )

        return redirect("/withdraw")

    # ----------------------------
    # Existing pending withdrawal
    # ----------------------------
    pending = Withdrawal.query.filter_by(
        user_id=current_user.id,
        status="Pending"
    ).first()

    if pending:
        flash(
            "You already have a pending withdrawal.",
            "warning"
        )
        return redirect("/withdraw")

    # ----------------------------
    # Create withdrawal request
    # ----------------------------
    withdrawal = Withdrawal(
        user_id=current_user.id,
        phone=phone,
        amount=amount,
        wallet="main",
        status="Pending",
        reference=f"WDL-{uuid4().hex[:10].upper()}"
    )

    db.session.add(withdrawal)
    db.session.commit()

    # ----------------------------
    # Send via IntaSend
    # ----------------------------
    success, response = send_mpesa_withdrawal(
        current_user,
        amount
    )

    if not success:

        db.session.delete(withdrawal)
        db.session.commit()

        flash(
            "Unable to initiate withdrawal. Please try again.",
            "danger"
        )

        return redirect("/withdraw")

    # Save IntaSend Tracking ID
    withdrawal.intasend_transaction_id = response.get("tracking_id")

    transactions = response.get("transactions", [])

    if transactions:
        withdrawal.intasend_reference = transactions[0].get("transaction_id")

    import json
    withdrawal.provider_response = json.dumps(response)

    db.session.add(
        Notification(
            user_id=current_user.id,
            title="Withdrawal Submitted",
            message=(
                f"Your withdrawal request of "
                f"KES {amount:.2f} is being processed."
            )
        )
    )

    db.session.commit()

    minimum_withdrawal = get_minimum_withdrawal(current_user.vip_level)
    required_contribution = get_required_contribution(current_user.vip_level)
    tracking_id = withdrawal.intasend_transaction_id
    print("VIP:", current_user.vip_level)
    print("Withdrawable Wallet:", current_user.withdrawable_wallet)
    print("Minimum Withdrawal:", minimum_withdrawal)
    print("Contribution:", current_user.referral_contribution_balance)
    print("Required:", required_contribution)
    print("Account Active:", current_user.account_active)
    return render_template(
        "withdraw_pending.html",
        tracking_id=tracking_id
    )

#-----------stauts check route
#----------withdrawal request route------------------
@app.route("/request-withdrawal", methods=["POST"])
@login_required
@active_account_required
def request_withdrawal():

    amount = float(request.form["amount"])

    allowed, message = can_withdraw(current_user)

    if not allowed:
        return jsonify({
            "success": False,
            "message": message
        })



    available_balance = get_withdrawable_balance(current_user)

    if amount > available_balance:

        return jsonify({
            "success": False,
            "message":
                f"You can only withdraw KES {available_balance:.2f}. "
                f"KES {locked_amount:.2f} is reserved for your {current_user.vip_level} membership."
        })

    MINIMUM = 500

    if amount < MINIMUM:

        return jsonify({
            "success": False,
            "message": f"Minimum withdrawal is KES {MINIMUM}."
        })

    existing = Withdrawal.query.filter_by(
        user_id=current_user.id,
        status="Pending"
    ).first()

    if existing:

        return jsonify({
            "success": False,
            "message": "You already have a pending withdrawal."
        })

    withdrawal = Withdrawal(
        user_id=current_user.id,
        phone=current_user.phone,
        amount=amount,
        status="Pending",
        reference=f"WD{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    )

    db.session.add(withdrawal)

    db.session.add(
        Notification(
            user_id=current_user.id,
            title="Withdrawal Requested",
            message=f"Your withdrawal request of KES {amount:.2f} has been received."
        )
    )

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Withdrawal request submitted successfully."
    })
#--------------stuatus check withdrawal route------------
@app.route("/check-withdrawal/<tracking_id>")
@login_required
@active_account_required
def check_withdrawal(tracking_id):

    withdrawal = Withdrawal.query.filter_by(
        intasend_transaction_id=tracking_id,
        user_id=current_user.id
    ).first()

    if not withdrawal:
        return jsonify({
            "status": "NOT_FOUND"
        })

    return jsonify({
        "status": withdrawal.status
    })
# ------------------ ADMIN WITHDRAWALS ------------------
@app.route("/admin/withdrawals")
@login_required
@admin_required
def admin_withdrawals():

    withdrawals = Withdrawal.query.order_by(
        Withdrawal.created_at.desc()
    ).all()

    pending = Withdrawal.query.filter_by(status="Pending").count()

    paid = Withdrawal.query.filter_by(status="Paid").count()

    failed = Withdrawal.query.filter_by(status="Failed").count()

    total_paid = db.session.query(
        db.func.sum(Withdrawal.amount)
    ).filter_by(status="Paid").scalar() or 0

    search = request.args.get("search", "")

    query = Withdrawal.query

    if search:

        query = query.join(User).filter(
            (User.username.ilike(f"%{search}%")) |
            (User.phone.ilike(f"%{search}%")) |
            (Withdrawal.reference.ilike(f"%{search}%"))
        )

    withdrawals = query.order_by(
        Withdrawal.created_at.desc()
    ).all()

    return render_template(
        "admin/withdrawals.html",
        withdrawals=withdrawals,
        pending=pending,
        paid=paid,
        failed=failed,
        total_paid=total_paid
    )
#---------------WITHDRAW VIEW ROUTES-------------
@app.route("/admin/withdrawal/<int:withdrawal_id>")
@login_required
@admin_required
def view_withdrawal(withdrawal_id):

    withdrawal = Withdrawal.query.get_or_404(withdrawal_id)

    return render_template(
        "admin/view_withdrawal.html",
        withdrawal=withdrawal
    )

#--------------WITHDRAWAL HISTORY------------------
@app.route("/withdrawal-history")
@login_required
@active_account_required
def withdrawal_history():

    withdrawals = Withdrawal.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Withdrawal.created_at.desc()
    ).all()

    return render_template(
        "withdrawal_history.html",
        withdrawals=withdrawals
    )
#-----------TRANSACTIONS-------------------
@app.route("/transactions")
@login_required
@active_account_required
def transaction_history():

    transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Transaction.created_at.desc()
    ).all()

    return render_template(
        "transactions.html",
        transactions=transactions
    )



    
#======================================================
if __name__ == "__main__":
    app.run(debug=True)
