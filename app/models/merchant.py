from datetime import datetime
from app.extensions import db


class Merchant(db.Model):
    __tablename__ = "merchants"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    business_name = db.Column(db.String(150), nullable=False)
    merchant_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    demo_upi_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False, default="Retail")
    location = db.Column(db.String(100), nullable=False, default="Metro Station Plaza")
    status = db.Column(db.String(20), nullable=False, default="ACTIVE")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="merchant_profile")

    def to_dict(self):
        return {
            "id": self.id,
            "business_name": self.business_name,
            "merchant_code": self.merchant_code,
            "demo_upi_id": self.demo_upi_id,
            "category": self.category,
            "location": self.location,
            "status": self.status,
            "owner_name": self.user.full_name if self.user else "Merchant Owner",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
