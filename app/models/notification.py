from datetime import datetime
from app.extensions import db


class NotificationType:
    PAYMENT_SUCCESS = "PAYMENT_SUCCESS"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    MONEY_RECEIVED = "MONEY_RECEIVED"
    PAYMENT_REQUEST = "PAYMENT_REQUEST"
    OTP_EVENT = "OTP_EVENT"
    SECURITY_ALERT = "SECURITY_ALERT"
    MERCHANT_PAYMENT = "MERCHANT_PAYMENT"
    REFUND = "REFUND"
    SYSTEM = "SYSTEM"


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), nullable=False, default=NotificationType.SYSTEM)
    reference_id = db.Column(db.String(50), nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = db.relationship("User", back_populates="notifications")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "type": self.type,
            "reference_id": self.reference_id,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
