from flask import Flask, render_template, request, redirect
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import re, random ,time
from flask_mail import Mail, Message

from models import db, User, Payment


app = Flask(__name__)

app.secret_key = "secret123"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ------------MAIL CONFIGURATION---------------
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'petersongitonga42@gmail.com'
app.config['MAIL_PASSWORD'] = 'elcq kybp kpvs pukm'

mail = Mail(app)
otp_store = {}

db.init_app(app)

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

# ---------------- HOME ----------------
@app.route("/")
def home():
    return redirect("/signup")


# ---------------- SIGNUP ----------------
@app.route("/signup", methods=["GET", "POST"])
def signup(): 
    if request.method == "POST":
        
        email = request.form["email"]
        phone = request.form["phone"]
        terms = request.form.get("terms")        # email regex
        email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"

        # kenya phone validation
        phone_pattern = r"^(07|01)\d{8}$"

        if not terms:
         return render_template("checkbox_alert.html")

        if not re.match(email_pattern, email):
            return "Invalid email format!"

        if not re.match(phone_pattern, phone):
            return "Invalid phone number!"
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return "Email already exists! Please login."

        hashed_pw = generate_password_hash(request.form["password"])

        new_user = User(
            username=request.form["username"],
            email=email,
            phone=phone,
            password=hashed_pw
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect("/payment")

    return render_template("signup.html")

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
            login_user(user)
            return redirect("/dashboard")

        return "Invalid username/email or password"

    return render_template("login.html")

#--------------PAYMENT-----------------
@app.route('/payment', methods=['GET', 'POST'])
def payment():

    if request.method == "POST":

        phone = request.form['phone']
        transaction_code = request.form['transaction_code']

        payment = Payment(
            phone=phone,
            transaction_code=transaction_code,
            amount=100,
            status='approved'
        )

        db.session.add(payment)
        db.session.commit()
        
        return redirect("/login")

    return render_template("payment.html")

# ---------------- DASHBOARD --------s--------
@app.route("/dashboard")
@login_required
def dashboard():

    payments = Payment.query.filter_by(phone=current_user.phone).all()

    total_paid = sum(p.amount for p in payments if p.status == "approved")

    return render_template(
        "dashboard.html",
        username=current_user.username,
        main_amount=total_paid
    )

# ---------------- LOGOUT ----------------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")



#--------------FORGOT PASSWORD------------
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        try:
            return "STEP 1"

        except Exception as e:
            return f"ERROR: {e}"

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





if __name__ == "__main__":
    app.run(debug=True)
