from game_engine import game
from flask import Flask, render_template, request, redirect,jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import re, random ,time,os
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

app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=30)

INTASEND_PUBLISHABLE_KEY = os.getenv("INTASEND_PUBLISHABLE_KEY")
INTASEND_SECRET_KEY = os.getenv("INTASEND_SECRET_KEY")

service = APIService(
    token=INTASEND_SECRET_KEY,
    publishable_key=INTASEND_PUBLISHABLE_KEY,
    test=False
)

# ------------MAIL CONFIGURATION---------------
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")

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

        if user:
            otp = str(random.randint(100000, 999999))

            otp_store[email] = {
                "otp": otp,
                "time": time.time()
            }

            msg = Message(
                "Password Reset OTP",
                sender=app.config['MAIL_USERNAME'],
                recipients=[email]
            )

            msg.body = f"Your OTP code is: {otp}"

            mail.send(msg)

            return redirect(f"/verify-otp/{email}")

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

    mail.send(msg)

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
                        referred_by=pending_user.referred_by
                    )

                    db.session.add(new_user)

                    # Save first so PostgreSQL assigns an ID
                    db.session.flush()

                    # Generate referral code
                    new_user.referral_code = f"SN{new_user.id}"

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


#------------AVIATOR GAME---------------------
@app.route("/aviator")
@login_required
def aviator():
    return render_template("aviator.html", username=current_user.username)


#------------------CREATE API ROUTE GAME--------------
@app.route("/game-state")
def game_state():

    return jsonify({

        "round": game.round_id,
        "status": game.status,
        "multiplier": round(game.multiplier, 2),
        "current_crash": game.current_crash,
        "countdown": game.countdown

    })

#----------------CREATE ADMIN API------------------
@app.route("/admin/game-state")
@login_required
def admin_game():

    if current_user.email != "petersongitonga02@gmail.com":
        return "Unauthorized", 403

    return jsonify({
        "round": game.round_id,
        "status": game.status,
        "current": round(game.multiplier, 2)
    })
#---------------------------------------------------------------
# START ROUND
@app.route("/admin/start-round", methods=["POST"])
@login_required
def start_round():

    if current_user.email != "petersongitonga02@gmail.com":
        return "Unauthorized", 403

    game.status = "flying"
    game.multiplier = 1.00

    return jsonify(success=True)
#---------------------------------------------------------------
#--------------------------increase multiplier-------------------
@app.route("/admin/increase", methods=["POST"])
@login_required
def increase():

    if current_user.email != "petersongitonga02@gmail.com":
        return "Unauthorized", 403

    if game.status == "flying":
        game.multiplier += 0.10

    return jsonify(multiplier=game.multiplier)

#------------------------decreasing multiplier---------------------
@app.route("/admin/decrease", methods=["POST"])
@login_required
def decrease():

    if current_user.email != "petersongitonga02@gmail.com":
        return "Unauthorized", 403

    if game.status == "flying" and game.multiplier > 1:
        game.multiplier -= 0.10

    return jsonify(multiplier=game.multiplier)

#-------------------------crash------------------------
@app.route("/admin/crash-round", methods=["POST"])
@login_required
def crash_round():

    if current_user.email != "petersongitonga02@gmail.com":
        return "Unauthorized", 403

    game.status = "crashed"

    return jsonify(success=True)

#--------------------=================---------------------



@app.route("/admin/aviator")
@login_required
def admin_aviator():

    if current_user.email != "petersongitonga02@gmail.com":
        return "Unauthorized", 403

    return render_template("admin_aviator.html")



#-------------------admin control route-----------------------

@app.route("/admin/start-round", methods=["POST"])
@login_required
def start_round():

    if current_user.email != "petersongitonga02@gmail.com":
        return "Unauthorized", 403

    game.status = "flying"
    game.multiplier = 1.00
    game.current_crash = round(random.uniform(1.20, 15.00), 2)

    return jsonify({"success": True})
    print("ADMIN STARTED ROUND")
    print(game.status)
    print(game.current_crash)

#------------------crash route-------------------
@app.route("/admin/crash-round", methods=["POST"])
@login_required
def crash_round():

    if current_user.email != "petersongitonga02@gmail.com":
        return "Unauthorized", 403

    game.status = "crashed"

    return jsonify({"success": True})


#-----------------------------------------------
    

if __name__ == "__main__":
    app.run(debug=True)
