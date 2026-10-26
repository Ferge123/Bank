import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from dotenv import load_dotenv
from models import db, User, Transaction, SecurityLog

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "robovault-super-secret-key-88")

# Database compatibility for Render
db_url = os.getenv("DATABASE_URL", "sqlite:///bank.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

from flask import has_request_context

# Helper to log security events
def log_event(event_type, details, user_id=None):
    ip = request.remote_addr if has_request_context() else '127.0.0.1'
    log = SecurityLog(user_id=user_id, event_type=event_type, details=details, ip_address=ip or '127.0.0.1')
    db.session.add(log)
    db.session.commit()

# Seed default admin on startup
with app.app_context():
    db.create_all()
    if not User.query.filter_by(role="admin").first():
        admin = User(
            username="admin",
            account_number="8800000001",
            role="admin",
            balance=1000000.0
        )
        admin.set_password("admin123")
        admin.set_pin("9999")
        db.session.add(admin)
        db.session.commit()
        log_event("SYSTEM_BOOT", "Master Admin seeded: username 'admin'")

def get_current_user():
    if "user_id" in session:
        return User.query.get(session["user_id"])
    return None

@app.route("/")
def index():
    user = get_current_user()
    if user:
        return redirect(url_for("admin_dashboard" if user.role == "admin" else "dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter((User.username == identifier) | (User.account_number == identifier)).first()

        if user and (user.check_password(password) or user.check_pin(password)):
            session["user_id"] = user.id
            session["role"] = user.role
            log_event("AUTH_SUCCESS", f"User {user.username} authenticated.", user.id)

            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("dashboard"))

        log_event("AUTH_FAILED", f"Failed login attempt for identifier: '{identifier}'")
        flash("Invalid Credentials. Please check username/account and PIN/password.", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    user = get_current_user()
    if user:
        log_event("SESSION_TERMINATED", f"User {user.username} logged out.", user.id)
    session.clear()
    flash("Session terminated securely.", "success")
    return redirect(url_for("login"))

# ================= CUSTOMER ROUTES =================

@app.route("/dashboard")
def dashboard():
    user = get_current_user()
    if not user or user.role != "customer":
        return redirect(url_for("login"))

    transactions = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.timestamp.desc()).limit(15).all()
    logs = SecurityLog.query.filter_by(user_id=user.id).order_by(SecurityLog.timestamp.desc()).limit(5).all()
    return render_template("dashboard.html", user=user, transactions=transactions, logs=logs)

@app.route("/api/deposit", methods=["POST"])
def deposit():
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    data = request.get_json() or {}
    try:
        amount = float(data.get("amount", 0))
    except ValueError:
        return jsonify({"success": False, "message": "Invalid amount"}), 400

    pin = data.get("pin", "")
    if not user.check_pin(pin):
        log_event("PIN_REJECTED", f"Deposit aborted: Incorrect PIN entered.", user.id)
        return jsonify({"success": False, "message": "Security Error: Invalid 4-digit PIN!"}), 403

    if amount <= 0:
        return jsonify({"success": False, "message": "Deposit amount must be positive."}), 400

    user.balance += amount
    sec_hash = Transaction.generate_hash(user.account_number, amount, "DEPOSIT")
    
    tx = Transaction(
        user_id=user.id,
        account_number=user.account_number,
        transaction_type="DEPOSIT",
        amount=amount,
        balance_after=user.balance,
        security_hash=sec_hash
    )
    db.session.add(tx)
    db.session.commit()

    log_event("DEPOSIT_SECURED", f"Deposited ${amount:,.2f}. Receipt Token: {sec_hash}", user.id)

    return jsonify({
        "success": True,
        "message": f"Successfully deposited ${amount:,.2f} into vault.",
        "new_balance": f"{user.balance:,.2f}",
        "security_token": sec_hash
    })

@app.route("/api/withdraw", methods=["POST"])
def withdraw():
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    data = request.get_json() or {}
    try:
        amount = float(data.get("amount", 0))
    except ValueError:
        return jsonify({"success": False, "message": "Invalid amount"}), 400

    pin = data.get("pin", "")
    if not user.check_pin(pin):
        log_event("PIN_REJECTED", f"Withdrawal aborted: Incorrect PIN entered.", user.id)
        return jsonify({"success": False, "message": "Security Error: Invalid 4-digit PIN!"}), 403

    if amount <= 0:
        return jsonify({"success": False, "message": "Amount must be greater than zero."}), 400

    if user.balance < amount:
        return jsonify({"success": False, "message": "Transaction Failed: Insufficient reserve funds."}), 400

    user.balance -= amount
    sec_hash = Transaction.generate_hash(user.account_number, amount, "WITHDRAWAL")

    tx = Transaction(
        user_id=user.id,
        account_number=user.account_number,
        transaction_type="WITHDRAWAL",
        amount=amount,
        balance_after=user.balance,
        security_hash=sec_hash
    )
    db.session.add(tx)
    db.session.commit()

    log_event("WITHDRAW_SECURED", f"Withdrew ${amount:,.2f}. Receipt Token: {sec_hash}", user.id)

    return jsonify({
        "success": True,
        "message": f"Dispensed ${amount:,.2f} from vault.",
        "new_balance": f"{user.balance:,.2f}",
        "security_token": sec_hash
    })

@app.route("/api/change-pin", methods=["POST"])
def change_pin():
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    data = request.get_json() or {}
    old_pin = data.get("old_pin", "")
    new_pin = data.get("new_pin", "")

    if not user.check_pin(old_pin):
        log_event("SECURITY_ALERT", "Failed PIN change attempt: Incorrect current PIN.", user.id)
        return jsonify({"success": False, "message": "Current PIN verification failed."}), 403

    if not new_pin.isdigit() or len(new_pin) != 4:
        return jsonify({"success": False, "message": "New PIN must be exactly 4 numeric digits."}), 400

    user.set_pin(new_pin)
    db.session.commit()
    log_event("SECURITY_UPDATE", "User successfully changed 4-digit security PIN.", user.id)

    return jsonify({"success": True, "message": "Security PIN updated and re-encrypted successfully!"})

# ================= ADMIN ROUTES =================

@app.route("/admin")
def admin_dashboard():
    user = get_current_user()
    if not user or user.role != "admin":
        return redirect(url_for("login"))

    customers = User.query.filter_by(role="customer").order_by(User.created_at.desc()).all()
    all_transactions = Transaction.query.order_by(Transaction.timestamp.desc()).limit(15).all()
    security_logs = SecurityLog.query.order_by(SecurityLog.timestamp.desc()).limit(20).all()
    total_reserves = sum(c.balance for c in customers)

    return render_template("admin.html", admin=user, customers=customers, 
                           transactions=all_transactions, logs=security_logs, total_reserves=total_reserves)

@app.route("/admin/create-customer", methods=["POST"])
def admin_create_customer():
    user = get_current_user()
    if not user or user.role != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    username = request.form.get("username", "").strip()
    default_pin = request.form.get("default_pin", "1234").strip()
    initial_balance = float(request.form.get("initial_balance", 1000.0))

    if not username:
        flash("Username is required.", "danger")
        return redirect(url_for("admin_dashboard"))

    if User.query.filter_by(username=username).first():
        flash("A customer with that username already exists.", "danger")
        return redirect(url_for("admin_dashboard"))

    new_customer = User(
        username=username,
        account_number=User.generate_account_number(),
        role="customer",
        balance=initial_balance
    )
    new_customer.set_password(default_pin)  # Initial password is default PIN
    new_customer.set_pin(default_pin)       # Security PIN is default PIN
    db.session.add(new_customer)
    db.session.commit()

    log_event("ADMIN_PROVISION", f"Admin created customer '{username}' with Acc #{new_customer.account_number} and default PIN '{default_pin}'", user.id)
    flash(f"New customer '{username}' provisioned! Acc: #{new_customer.account_number} (Default PIN: {default_pin})", "success")
    return redirect(url_for("admin_dashboard"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)