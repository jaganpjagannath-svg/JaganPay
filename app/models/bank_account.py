from datetime import datetime
from app.extensions import db


class BankNames:
    JAGAN_BANK = "Jagan Bank"
    ASTRA_BANK = "Astra Bank"
    DEMO_NATIONAL = "Demo National Bank"

    ALL = [JAGAN_BANK, ASTRA_BANK, DEMO_NATIONAL]


class DemoBankAccount(db.Model):
    __tablename__ = "demo_bank_accounts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    bank_name = db.Column(db.String(100), nullable=False, default=BankNames.JAGAN_BANK)
    account_holder = db.Column(db.String(120), nullable=False)
    account_number_masked = db.Column(db.String(30), nullable=False)
    ifsc_code = db.Column(db.String(20), nullable=False, default="JAGB0001001")
    account_type = db.Column(db.String(20), nullable=False, default="SAVINGS")
    demo_balance = db.Column(db.Float, nullable=False, default=25000.0)
    is_primary = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="bank_accounts")

    def to_dict(self):
        return {
            "id": self.id,
            "bank_name": self.bank_name,
            "account_holder": self.account_holder,
            "account_number_masked": self.account_number_masked,
            "ifsc_code": self.ifsc_code,
            "account_type": self.account_type,
            "demo_balance": float(self.demo_balance),
            "is_primary": self.is_primary,
            "is_simulated": True,
        }


class UPIProfile(db.Model):
    __tablename__ = "upi_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    upi_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    qr_data = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="upi_profile")

    def to_dict(self):
        return {
            "id": self.id,
            "upi_id": self.upi_id,
            "qr_data": self.qr_data,
            "is_active": self.is_active,
            "is_simulated": True,
        }
