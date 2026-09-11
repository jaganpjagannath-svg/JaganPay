import os
import sys
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app import create_app
from app.extensions import db
from app.models.user import User, Role
from app.models.bank_account import DemoBankAccount, UPIProfile, BankNames
from app.models.merchant import Merchant
from app.models.transaction import (
    Transaction, PaymentRequest, TransactionType, TransactionStatus, SpendingCategory, RiskLevel
)
from app.models.notification import Notification, NotificationType
from app.models.security import SecurityEvent, AuditLog, RiskAlert
from app.models.support import SupportTicket, SupportMessage, TicketStatus, TicketPriority
from app.utils.helpers import generate_reference_no


def seed_database():
    app = create_app()
    with app.app_context():
        print("[*] Seeding JaganPay Demo Platform Data...")

        # 1. Clear existing demo data
        db.drop_all()
        db.create_all()

        # 2. Demo Users
        users_data = [
            {"name": "Jagan Varma", "email": "jagan@jaganpay.com", "phone": "+919800000001", "upi": "jagan@jaganpay", "role": Role.ADMIN, "balance": 75000.0},
            {"name": "Demo User", "email": "demo@jaganpay.com", "phone": "+919800000002", "upi": "demo@jaganpay", "role": Role.USER, "balance": 25000.0},
            {"name": "Aarav Sharma", "email": "aarav@jaganpay.com", "phone": "+919800000003", "upi": "aarav@jaganpay", "role": Role.USER, "balance": 18500.0},
            {"name": "Riya Patel", "email": "riya@jaganpay.com", "phone": "+919800000004", "upi": "riya@jaganpay", "role": Role.USER, "balance": 34200.0},
            {"name": "Vikram Malhotra", "email": "vikram@jaganpay.com", "phone": "+919800000005", "upi": "vikram@jaganpay", "role": Role.USER, "balance": 42000.0},
            {"name": "Ananya Sen", "email": "ananya@jaganpay.com", "phone": "+919800000006", "upi": "ananya@jaganpay", "role": Role.USER, "balance": 15000.0},
            {"name": "Campus Canteen Owner", "email": "canteen@jaganpay.com", "phone": "+919800000007", "upi": "canteen@jaganpay", "role": Role.MERCHANT, "balance": 95000.0},
            {"name": "Jagan Cafe Manager", "email": "jagancafe@jaganpay.com", "phone": "+919800000008", "upi": "jagancafe@jaganpay", "role": Role.MERCHANT, "balance": 128000.0},
            {"name": "Astra Retailer", "email": "astra@jaganpay.com", "phone": "+919800000009", "upi": "astrastore@jaganpay", "role": Role.MERCHANT, "balance": 210000.0},
        ]

        created_users = {}
        for u in users_data:
            user = User(
                full_name=u["name"],
                email=u["email"],
                phone=u["phone"],
                role=u["role"],
                is_verified=True,
                is_active=True,
            )
            # Default password for all demo users
            user.set_password("DemoPassword123!")
            user.set_pin("1234")
            db.session.add(user)
            db.session.flush()

            # UPI Profile
            upi_prof = UPIProfile(
                user_id=user.id,
                upi_id=u["upi"],
                qr_data=f"upi://pay?pa={u['upi']}&pn={user.full_name}&cu=INR&mode=02",
                is_active=True,
            )
            db.session.add(upi_prof)

            # Bank Account
            bank_name = random.choice(BankNames.ALL)
            acc = DemoBankAccount(
                user_id=user.id,
                bank_name=bank_name,
                account_holder=user.full_name,
                account_number_masked=f"•••• •••• {user.phone[-4:]}",
                ifsc_code=f"{bank_name[:4].upper()}0001001",
                account_type="SAVINGS" if u["role"] != Role.MERCHANT else "CURRENT",
                demo_balance=u["balance"],
                is_primary=True,
            )
            db.session.add(acc)

            created_users[u["upi"]] = user

        db.session.commit()
        print(f"Created {len(users_data)} demo users with UPI profiles and bank accounts.")

        # 3. Seed Merchants
        merchants_data = [
            {"user_upi": "jagancafe@jaganpay", "biz_name": "Jagan Cafe", "code": "MERCH-JAGANCAFE", "upi": "jagancafe@jaganpay", "category": "Food & Dining", "loc": "Cyber Towers, Hyderabad"},
            {"user_upi": "astrastore@jaganpay", "biz_name": "Astra Store", "code": "MERCH-ASTRASTORE", "upi": "astrastore@jaganpay", "category": "Electronics & Gadgets", "loc": "MG Road, Bengaluru"},
            {"user_upi": "canteen@jaganpay", "biz_name": "Campus Canteen", "code": "MERCH-CAMPUSCANTEEN", "upi": "canteen@jaganpay", "category": "Cafeteria & Snacks", "loc": "University North Block"},
        ]

        for m in merchants_data:
            user = created_users[m["user_upi"]]
            merchant = Merchant(
                user_id=user.id,
                business_name=m["biz_name"],
                merchant_code=m["code"],
                demo_upi_id=m["upi"],
                category=m["category"],
                location=m["loc"],
                status="ACTIVE",
            )
            db.session.add(merchant)

        db.session.commit()
        print("Created 3 demo merchants.")

        # 4. Seed Simulated Transactions
        jagan_user = created_users["jagan@jaganpay"]
        demo_user = created_users["demo@jaganpay"]
        cafe_user = created_users["jagancafe@jaganpay"]
        astra_user = created_users["astrastore@jaganpay"]

        sample_txns = [
            {"sender": jagan_user, "receiver": cafe_user, "amount": 420.0, "type": TransactionType.MERCHANT_PAYMENT, "cat": SpendingCategory.FOOD, "desc": "Filter Coffee & Croissant", "days_ago": 1, "risk": 12, "status": TransactionStatus.SUCCESS},
            {"sender": jagan_user, "receiver": demo_user, "amount": 1500.0, "type": TransactionType.SEND, "cat": SpendingCategory.OTHER, "desc": "Split weekend dinner", "days_ago": 2, "risk": 15, "status": TransactionStatus.SUCCESS},
            {"sender": demo_user, "receiver": jagan_user, "amount": 3500.0, "type": TransactionType.SEND, "cat": SpendingCategory.OTHER, "desc": "Project hackathon reimbursement", "days_ago": 3, "risk": 10, "status": TransactionStatus.SUCCESS},
            {"sender": jagan_user, "receiver": astra_user, "amount": 14999.0, "type": TransactionType.QR_PAYMENT, "cat": SpendingCategory.SHOPPING, "desc": "Wireless Mechanical Keyboard & Desk Mat", "days_ago": 4, "risk": 38, "status": TransactionStatus.SUCCESS},
            {"sender": jagan_user, "receiver": created_users["riya@jaganpay"], "amount": 750.0, "type": TransactionType.SEND, "cat": SpendingCategory.ENTERTAINMENT, "desc": "Movie tickets booking", "days_ago": 5, "risk": 10, "status": TransactionStatus.SUCCESS},
            {"sender": created_users["aarav@jaganpay"], "receiver": jagan_user, "amount": 1200.0, "type": TransactionType.SEND, "cat": SpendingCategory.OTHER, "desc": "Shared cab fare", "days_ago": 6, "risk": 10, "status": TransactionStatus.SUCCESS},
            {"sender": jagan_user, "receiver": cafe_user, "amount": 250.0, "type": TransactionType.MERCHANT_PAYMENT, "cat": SpendingCategory.FOOD, "desc": "Cold brew recharge", "days_ago": 7, "risk": 10, "status": TransactionStatus.SUCCESS},
            {"sender": jagan_user, "receiver": astra_user, "amount": 55000.0, "type": TransactionType.SEND, "cat": SpendingCategory.SHOPPING, "desc": "High value demo transfer", "days_ago": 0, "risk": 82, "status": TransactionStatus.SUCCESS},
            {"sender": jagan_user, "receiver": demo_user, "amount": 8000.0, "type": TransactionType.SEND, "cat": SpendingCategory.BILLS, "desc": "Electricity & Wifi demo bill", "days_ago": 8, "risk": 20, "status": TransactionStatus.SUCCESS},
        ]

        for st in sample_txns:
            created_dt = datetime.utcnow() - timedelta(days=st["days_ago"], hours=random.randint(1, 10))
            txn = Transaction(
                reference_no=generate_reference_no("JGP"),
                sender_id=st["sender"].id,
                receiver_id=st["receiver"].id,
                sender_upi=st["sender"].primary_upi,
                receiver_upi=st["receiver"].primary_upi,
                amount=st["amount"],
                fee=0.0,
                type=st["type"],
                status=st["status"],
                category=st["cat"],
                description=st["desc"],
                risk_score=st["risk"],
                risk_level=RiskLevel.HIGH if st["risk"] >= 65 else (RiskLevel.MEDIUM if st["risk"] >= 35 else RiskLevel.LOW),
                created_at=created_dt,
            )
            db.session.add(txn)
            db.session.flush()

            # If High Risk, add a RiskAlert
            if txn.risk_level == RiskLevel.HIGH:
                alert = RiskAlert(
                    transaction_id=txn.id,
                    user_id=st["sender"].id,
                    risk_score=st["risk"],
                    risk_level=RiskLevel.HIGH,
                    factors="Very large simulated transfer (> ₹50,000), Velocity spike",
                    status="PENDING_REVIEW",
                    created_at=created_dt,
                )
                db.session.add(alert)

        db.session.commit()
        print("Created simulated transactions and risk alerts.")

        # 5. Payment Requests
        req1 = PaymentRequest(
            requester_id=demo_user.id,
            payer_upi="jagan@jaganpay",
            amount=850.0,
            description="Lunch split at campus canteen",
            status="PENDING",
            expires_at=datetime.utcnow() + timedelta(days=2),
        )
        db.session.add(req1)

        req2 = PaymentRequest(
            requester_id=jagan_user.id,
            payer_upi="riya@jaganpay",
            amount=1400.0,
            description="Concert ticket share",
            status="PENDING",
            expires_at=datetime.utcnow() + timedelta(days=3),
        )
        db.session.add(req2)

        # 6. Notifications
        notif1 = Notification(
            user_id=jagan_user.id,
            title="Demo Credit Received",
            message="You received ₹3,500.00 from Demo User (Ref: JGP2026090812345).",
            type=NotificationType.MONEY_RECEIVED,
            is_read=False,
        )
        notif2 = Notification(
            user_id=jagan_user.id,
            title="Payment Request Received",
            message="Demo User requested ₹850.00 for 'Lunch split at campus canteen'.",
            type=NotificationType.PAYMENT_REQUEST,
            is_read=False,
        )
        notif3 = Notification(
            user_id=jagan_user.id,
            title="Welcome to JaganPay",
            message="Your demo account has been initialized with ₹75,000 simulated balance.",
            type=NotificationType.SYSTEM,
            is_read=True,
        )
        db.session.add_all([notif1, notif2, notif3])

        # 7. Support Tickets
        ticket1 = SupportTicket(
            ticket_no=SupportTicket.generate_ticket_no(),
            user_id=jagan_user.id,
            subject="Question regarding simulated QR payment expiration",
            category="GENERAL",
            priority=TicketPriority.LOW,
            description="Do generated demo payment request QR codes have a 15-minute expiration period like standard UPI?",
            status=TicketStatus.OPEN,
        )
        db.session.add(ticket1)
        db.session.flush()

        msg1 = SupportMessage(
            ticket_id=ticket1.id,
            sender_id=jagan_user.id,
            sender_name=jagan_user.full_name,
            message=ticket1.description,
            is_admin_reply=False,
        )
        db.session.add(msg1)

        # 8. Audit Logs
        audit1 = AuditLog(
            user_id=jagan_user.id,
            user_email=jagan_user.email,
            action="USER_LOGIN",
            entity_type="USER",
            entity_id=jagan_user.id,
            result="SUCCESS",
            details='{"method": "password_and_session"}',
        )
        audit2 = AuditLog(
            user_id=jagan_user.id,
            user_email=jagan_user.email,
            action="PAYMENT_SUCCESS",
            entity_type="TRANSACTION",
            entity_id="JGP202609110001",
            result="SUCCESS",
            details='{"amount": 420.0, "receiver": "jagancafe@jaganpay"}',
        )
        db.session.add_all([audit1, audit2])

        db.session.commit()
        print("[OK] Database successfully seeded with rich demo data!")
        print("\nDemo Accounts Created:")
        print("1. Admin / Primary User: jagan@jaganpay.com / DemoPassword123! (PIN: 1234, UPI: jagan@jaganpay)")
        print("2. Demo User:           demo@jaganpay.com  / DemoPassword123! (PIN: 1234, UPI: demo@jaganpay)")
        print("3. Merchant User:       jagancafe@jaganpay.com / DemoPassword123! (PIN: 1234, UPI: jagancafe@jaganpay)")


if __name__ == "__main__":
    seed_database()
