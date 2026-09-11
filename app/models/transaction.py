import uuid
from datetime import datetime
from app.extensions import db


class TransactionType:
    SEND = "SEND"
    RECEIVE = "RECEIVE"
    REQUEST = "REQUEST"
    MERCHANT_PAYMENT = "MERCHANT_PAYMENT"
    QR_PAYMENT = "QR_PAYMENT"
    REFUND = "REFUND"
    CASHBACK = "CASHBACK"
    RECHARGE_SIMULATION = "RECHARGE_SIMULATION"

    ALL = [SEND, RECEIVE, REQUEST, MERCHANT_PAYMENT, QR_PAYMENT, REFUND, CASHBACK, RECHARGE_SIMULATION]


class TransactionStatus:
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"

    ALL = [PENDING, PROCESSING, SUCCESS, FAILED, CANCELLED, REFUNDED]


class SpendingCategory:
    FOOD = "FOOD"
    SHOPPING = "SHOPPING"
    TRAVEL = "TRAVEL"
    ENTERTAINMENT = "ENTERTAINMENT"
    BILLS = "BILLS"
    EDUCATION = "EDUCATION"
    HEALTHCARE = "HEALTHCARE"
    OTHER = "OTHER"

    ALL = [FOOD, SHOPPING, TRAVEL, ENTERTAINMENT, BILLS, EDUCATION, HEALTHCARE, OTHER]


class RiskLevel:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reference_no = db.Column(db.String(32), unique=True, nullable=False, index=True)
    sender_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    receiver_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    sender_upi = db.Column(db.String(100), nullable=False)
    receiver_upi = db.Column(db.String(100), nullable=False, index=True)
    sender_account_id = db.Column(db.Integer, db.ForeignKey("demo_bank_accounts.id", ondelete="SET NULL"), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    fee = db.Column(db.Float, default=0.0, nullable=False)
    type = db.Column(db.String(30), nullable=False, default=TransactionType.SEND, index=True)
    status = db.Column(db.String(20), nullable=False, default=TransactionStatus.SUCCESS, index=True)
    category = db.Column(db.String(30), nullable=False, default=SpendingCategory.OTHER, index=True)
    description = db.Column(db.String(255), nullable=True)
    risk_score = db.Column(db.Integer, default=10, nullable=False)
    risk_level = db.Column(db.String(10), default=RiskLevel.LOW, nullable=False)
    failure_reason = db.Column(db.String(255), nullable=True)
    is_simulated = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    sender = db.relationship("User", foreign_keys=[sender_id], back_populates="sent_transactions")
    receiver = db.relationship("User", foreign_keys=[receiver_id], back_populates="received_transactions")
    sender_account = db.relationship("DemoBankAccount")
    risk_alerts = db.relationship("RiskAlert", back_populates="transaction", cascade="all, delete-orphan", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "reference_no": self.reference_no,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "sender_name": self.sender.full_name if self.sender else "Demo User",
            "receiver_name": self.receiver.full_name if self.receiver else "Demo Recipient",
            "sender_upi": self.sender_upi,
            "receiver_upi": self.receiver_upi,
            "amount": float(self.amount),
            "fee": float(self.fee),
            "type": self.type,
            "status": self.status,
            "category": self.category,
            "description": self.description,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "is_simulated": True,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PaymentRequest(db.Model):
    __tablename__ = "payment_requests"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    requester_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    payer_upi = db.Column(db.String(100), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default="PENDING", nullable=False)  # PENDING, PAID, REJECTED, EXPIRED
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)

    requester = db.relationship("User", foreign_keys=[requester_id], back_populates="payment_requests_sent")

    def to_dict(self):
        return {
            "id": self.id,
            "requester_id": self.requester_id,
            "requester_name": self.requester.full_name if self.requester else "User",
            "requester_upi": self.requester.primary_upi if self.requester else "",
            "payer_upi": self.payer_upi,
            "amount": float(self.amount),
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
