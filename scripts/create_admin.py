import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app import create_app
from app.extensions import db
from app.models.user import User, Role
from app.models.bank_account import DemoBankAccount, UPIProfile, BankNames


def create_admin_user(email="admin@jaganpay.com", password="AdminPassword123!", name="JaganPay Administrator"):
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if user:
            print(f"User with email {email} already exists. Elevating to ADMIN...")
            user.role = Role.ADMIN
            user.is_verified = True
            user.is_active = True
            user.set_password(password)
            user.set_pin("1234")
            db.session.commit()
            print("Admin credentials updated successfully.")
            return

        admin = User(
            full_name=name,
            email=email,
            phone="+919876543210",
            role=Role.ADMIN,
            is_verified=True,
            is_active=True,
        )
        admin.set_password(password)
        admin.set_pin("1234")
        db.session.add(admin)
        db.session.commit()

        # UPI Profile
        upi = UPIProfile(
            user_id=admin.id,
            upi_id="admin@jaganpay",
            qr_data="upi://pay?pa=admin@jaganpay&pn=JaganPayAdmin&cu=INR&mode=02",
        )
        db.session.add(upi)

        # Demo Bank Account
        acc = DemoBankAccount(
            user_id=admin.id,
            bank_name=BankNames.JAGAN_BANK,
            account_holder=name,
            account_number_masked="•••• •••• 9999",
            ifsc_code="JAGB0001001",
            account_type="SAVINGS",
            demo_balance=100000.0,
            is_primary=True,
        )
        db.session.add(acc)
        db.session.commit()

        print(f"✅ Admin created successfully!")
        print(f"   Email:    {email}")
        print(f"   Password: {password}")
        print(f"   Demo PIN: 1234")
        print(f"   UPI ID:   admin@jaganpay")


if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "admin@jaganpay.com"
    password = sys.argv[2] if len(sys.argv) > 2 else "AdminPassword123!"
    create_admin_user(email, password)
