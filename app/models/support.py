import random
from datetime import datetime
from app.extensions import db


class TicketStatus:
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

    ALL = [OPEN, IN_PROGRESS, RESOLVED, CLOSED]


class TicketPriority:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class SupportTicket(db.Model):
    __tablename__ = "support_tickets"

    id = db.Column(db.Integer, primary_key=True)
    ticket_no = db.Column(db.String(20), unique=True, nullable=False, index=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subject = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False, default="GENERAL")
    description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), nullable=False, default=TicketPriority.MEDIUM)
    status = db.Column(db.String(20), nullable=False, default=TicketStatus.OPEN, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="support_tickets")
    messages = db.relationship("SupportMessage", back_populates="ticket", cascade="all, delete-orphan", lazy="dynamic", order_by="SupportMessage.created_at")

    @classmethod
    def generate_ticket_no(cls) -> str:
        return f"TKT-{random.randint(10000, 99999)}"

    def to_dict(self):
        return {
            "id": self.id,
            "ticket_no": self.ticket_no,
            "user_id": self.user_id,
            "user_name": self.user.full_name if self.user else "User",
            "user_email": self.user.email if self.user else "user@jaganpay",
            "subject": self.subject,
            "category": self.category,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "messages_count": self.messages.count(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SupportMessage(db.Model):
    __tablename__ = "support_messages"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    sender_name = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_admin_reply = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    ticket = db.relationship("SupportTicket", back_populates="messages")
    sender = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "sender_name": self.sender_name,
            "message": self.message,
            "is_admin_reply": self.is_admin_reply,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
