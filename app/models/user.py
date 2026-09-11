import uuid
from datetime import datetime
from flask_login import UserMixin
from app.extensions import db, bcrypt


class Role:
    USER = "USER"
    MERCHANT = "MERCHANT"
    ADMIN = "ADMIN"

    ALL = [USER, MERCHANT, ADMIN]


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    demo_pin_hash = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(20), nullable=False, default=Role.USER, index=True)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    profile_pic_url = db.Column(db.String(255), nullable=True)
    last_login_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    bank_accounts = db.relationship("DemoBankAccount", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    upi_profile = db.relationship("UPIProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sent_transactions = db.relationship("Transaction", foreign_keys="Transaction.sender_id", back_populates="sender", lazy="dynamic")
    received_transactions = db.relationship("Transaction", foreign_keys="Transaction.receiver_id", back_populates="receiver", lazy="dynamic")
    payment_requests_sent = db.relationship("PaymentRequest", foreign_keys="PaymentRequest.requester_id", back_populates="requester", lazy="dynamic")
    notifications = db.relationship("Notification", back_populates="user", cascade="all, delete-orphan", lazy="dynamic", order_by="desc(Notification.created_at)")
    security_events = db.relationship("SecurityEvent", back_populates="user", cascade="all, delete-orphan", lazy="dynamic", order_by="desc(SecurityEvent.created_at)")
    support_tickets = db.relationship("SupportTicket", back_populates="user", cascade="all, delete-orphan", lazy="dynamic", order_by="desc(SupportTicket.created_at)")
    merchant_profile = db.relationship("Merchant", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def set_password(self, password: str):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return bcrypt.check_password_hash(self.password_hash, password)

    def set_pin(self, pin: str):
        self.demo_pin_hash = bcrypt.generate_password_hash(pin).decode("utf-8")

    def check_pin(self, pin: str) -> bool:
        if not self.demo_pin_hash:
            return False
        return bcrypt.check_password_hash(self.demo_pin_hash, pin)

    @property
    def has_pin(self) -> bool:
        return self.demo_pin_hash is not None

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    @property
    def is_merchant(self) -> bool:
        return self.role == Role.MERCHANT or self.merchant_profile is not None

    @property
    def primary_upi(self) -> str:
        if self.upi_profile:
            return self.upi_profile.upi_id
        return f"{self.email.split('@')[0]}@jaganpay"

    @property
    def total_demo_balance(self) -> float:
        accounts = self.bank_accounts.all()
        return sum(acc.demo_balance for acc in accounts) if accounts else 0.0

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "role": self.role,
            "is_verified": self.is_verified,
            "is_active": self.is_active,
            "has_pin": self.has_pin,
            "primary_upi": self.primary_upi,
            "total_demo_balance": float(self.total_demo_balance),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
