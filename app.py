from game_engine import game
from flask import Flask, render_template, request, redirect,jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import re, random ,time,os,requests
from flask_mail import Mail, Message
from models import db, User, Payment, PendingUser
from flask_sqlalchemy import SQLAlchemy
from intasend import APIService
from dotenv import load_dotenv

from datetime import timedelta
from flask_migrate import Migrate



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
    ref = request.args.get("ref")

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
                amount=10,
                status="pending"
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

# ---------------- DASHBOARD --------s--------
@app.route("/dashboard")
@login_required
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

    return render_template(
        "dashboard.html",
        username=current_user.username,
        main_amount=total_paid,
        referral_link=referral_link,
        total_referrals=total_referrals
    )

# ---------------- LOGOUT ----------------
@app.route("/logout")
@login_required
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

    print("WEBHOOK RECEIVED:")
    print(data)

    invoice_id = data.get("invoice_id")
    state = data.get("state")

    print("INVOICE:", invoice_id)
    print("STATE:", state)

    payment = Payment.query.filter_by(
        transaction_code=invoice_id
    ).first()

    print("PAYMENT FOUND:", payment)

    if payment:

        if state in ["COMPLETE", "COMPLETED", "SUCCESSFUL"]:

            payment.status = "approved"

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
                    task_wallet=0,
                    team_wallet=0,
                    total_withdrawn=0,
                    today_earnings=0,
                    commissions=0
                )
                
                db.session.add(new_user)
                
                # Get user ID
                db.session.flush()
                
                # Referral code
                new_user.referral_code = f"SN{new_user.id}"
                
                # -----------------------------------------
                # Give referral commission
                # -----------------------------------------
                
                if new_user.referred_by:
                
                    referrer = User.query.filter_by(
                        referral_code=new_user.referred_by
                    ).first()
                
                    if referrer:
                
                        add_to_team_wallet(
                            referrer,
                            150,
                            f"Referral bonus from {new_user.username}"
                        )
                
                        referrer.commissions += 150
                
                        print(
                            f"Referral bonus awarded to {referrer.username}"
                        )
                
                print("USER CREATED:", pending_user.username)
                print("REFERRAL CODE:", new_user.referral_code)
                print("REFERRED BY:", new_user.referred_by)

                db.session.delete(pending_user)

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


#-----------TENPORARY ROUT---------------
@app.route("/users")
def users():
    all_users = User.query.all()

    html = ""

    for user in all_users:
        html += f"""
        <p>
        {user.id} |
        {user.username} |
        {user.email} |
        {user.phone}
        </p>
        """

    return html
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

#=====================WALLETS HELPERS FUNCTIONS================================
def add_to_main_wallet(user, amount, description):

    user.main_wallet += amount

    transaction = Transaction(
        user_id=user.id,
        transaction_type="credit",
        wallet="Main",
        amount=amount,
        description=description
    )

    db.session.add(transaction)

def add_to_task_wallet(user, amount, description):

    user.task_wallet += amount

    transaction = Transaction(
        user_id=user.id,
        transaction_type="credit",
        wallet="Task",
        amount=amount,
        description=description
    )

    db.session.add(transaction)

def add_to_team_wallet(user, amount, description):

    user.team_wallet += amount

    transaction = Transaction(
        user_id=user.id,
        transaction_type="credit",
        wallet="Team",
        amount=amount,
        description=description
    )

    db.session.add(transaction)




#========================================================================
if __name__ == "__main__":
    app.run(debug=True)
