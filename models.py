from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random
import hashlib

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    account_number = db.Column(db.String(10), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    pin_hash = db.Column(db.String(255), nullable=False)  # 4-digit security PIN
    role = db.Column(db.String(20), default='customer')    # 'admin' or 'customer'
    balance = db.Column(db.Float, default=1000.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_pin(self, pin):
        self.pin_hash = generate_password_hash(str(pin))

    def check_pin(self, pin):
        return check_password_hash(self.pin_hash, str(pin))

    @staticmethod
    def generate_account_number():
        return str(random.randint(8800000000, 8899999999))

class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    account_number = db.Column(db.String(10), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # DEPOSIT, WITHDRAWAL
    amount = db.Column(db.Float, nullable=False)
    balance_after = db.Column(db.Float, nullable=False)
    security_hash = db.Column(db.String(64), nullable=False)     # Cryptographic receipt
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def generate_hash(account, amount, tx_type):
        raw = f"{account}:{amount}:{tx_type}:{datetime.utcnow().timestamp()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16].upper()

class SecurityLog(db.Model):
    __tablename__ = 'security_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    event_type = db.Column(db.String(50), nullable=False)
    details = db.Column(db.String(255), nullable=False)
    ip_address = db.Column(db.String(45), default='127.0.0.1')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)