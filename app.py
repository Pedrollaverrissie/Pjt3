from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import re
from models import db, User, Payment

app = Flask(__name__)
app.secret_key = "secret123"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

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

        # email regex
        email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"

        # kenya phone validation
        phone_pattern = r"^(07|01)\d{8}$"

        if not re.match(email_pattern, email):
            return "Invalid email format!"

        if not re.match(phone_pattern, phone):
            return "Invalid phone number!"

        hashed_pw = generate_password_hash(request.form["password"])

        new_user = User(
            username=request.form["username"],
            email=email,
            phone=phone,
            password=hashed_pw
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect("/login")

    return render_template("signup.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(email=request.form["email"]).first()

        if user and check_password_hash(user.password, request.form["password"]):
            login_user(user)
            return redirect("/dashboard")

        return "Invalid credentials"

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

if __name__ == "__main__":
    app.run(debug=True)
