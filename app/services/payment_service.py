import logging
from flask import current_app
from app.extensions import db
from app.models.user import User
from app.models.bank_account import DemoBankAccount, UPIProfile
from app.models.transaction import (
    Transaction, TransactionType, TransactionStatus, SpendingCategory, RiskLevel
)
from app.models.security import RiskAlert
from app.models.notification import NotificationType
from app.services.risk_service import calculate_simulated_risk
from app.services.notification_service import create_notification
from app.services.webhook_service import dispatch_event
from app.services.audit_service import log_audit, log_security_event
from app.utils.helpers import generate_reference_no, format_currency

logger = logging.getLogger("jaganpay.payments")


def execute_simulated_transfer(
    sender: User,
    receiver_upi: str,
    amount: float,
    description: str = "Demo Transfer",
    category: str = SpendingCategory.OTHER,
    txn_type: str = TransactionType.SEND,
    account_id: int = None,
) -> tuple[bool, str, Transaction | None]:
    """
    Executes an atomic simulated transfer between sender and receiver UPI.
    Safely adjusts demo balances, generates transaction ledger, risk score,
    notifications, and triggers n8n webhooks.
    """
    if amount <= 0:
        return False, "Amount must be greater than zero.", None

    receiver_upi = receiver_upi.strip().lower()

    # Find sender's primary or selected demo bank account
    if account_id:
        sender_account = DemoBankAccount.query.filter_by(id=account_id, user_id=sender.id).first()
    else:
        sender_account = DemoBankAccount.query.filter_by(user_id=sender.id, is_primary=True).first()
        if not sender_account:
            sender_account = DemoBankAccount.query.filter_by(user_id=sender.id).first()

    if not sender_account:
        return False, "No active demo bank account found. Please link a simulated account.", None

    if sender_account.demo_balance < amount:
        return False, f"Insufficient demo balance. Available: {format_currency(sender_account.demo_balance)}", None

    if sender.primary_upi.lower() == receiver_upi:
        return False, "You cannot send demo money to your own UPI ID.", None

    # Resolve receiver
    receiver_profile = UPIProfile.query.filter_by(upi_id=receiver_upi).first()
    receiver_user = receiver_profile.user if receiver_profile else None
    receiver_account = None

    if receiver_user:
        receiver_account = DemoBankAccount.query.filter_by(user_id=receiver_user.id, is_primary=True).first()
        if not receiver_account:
            receiver_account = DemoBankAccount.query.filter_by(user_id=receiver_user.id).first()

    # Calculate simulated risk score
    risk_score, risk_level, risk_factors = calculate_simulated_risk(
        sender_id=sender.id,
        receiver_upi=receiver_upi,
        amount=amount
    )

    ref_no = generate_reference_no("JGP")

    try:
        # Atomic balance mutation
        sender_account.demo_balance -= amount

        if receiver_account:
            receiver_account.demo_balance += amount

        txn = Transaction(
            reference_no=ref_no,
            sender_id=sender.id,
            receiver_id=receiver_user.id if receiver_user else None,
            sender_upi=sender.primary_upi,
            receiver_upi=receiver_upi,
            sender_account_id=sender_account.id,
            amount=amount,
            fee=0.0,
            type=txn_type,
            status=TransactionStatus.SUCCESS,
            category=category if category in SpendingCategory.ALL else SpendingCategory.OTHER,
            description=description or "Demo UPI Payment",
            risk_score=risk_score,
            risk_level=risk_level,
            is_simulated=True,
        )
        db.session.add(txn)

        # High risk alert generation
        if risk_level == RiskLevel.HIGH:
            alert = RiskAlert(
                transaction_id=txn.id,
                user_id=sender.id,
                risk_score=risk_score,
                risk_level=risk_level,
                factors=", ".join(risk_factors),
                status="PENDING_REVIEW",
            )
            db.session.add(alert)

            # Dispatch risk alert webhook
            dispatch_event("RISK_ALERT", {
                "transaction_id": txn.id,
                "reference_no": ref_no,
                "user_email": sender.email,
                "amount": amount,
                "risk_score": risk_score,
                "factors": risk_factors,
            })

        db.session.commit()

        # Send notifications
        create_notification(
            user_id=sender.id,
            title="Payment Sent Successfully",
            message=f"Simulated payment of {format_currency(amount)} sent to {receiver_upi} (Ref: {ref_no}).",
            notif_type=NotificationType.PAYMENT_SUCCESS,
            reference_id=ref_no
        )

        if receiver_user:
            create_notification(
                user_id=receiver_user.id,
                title="Demo Money Received",
                message=f"Received {format_currency(amount)} from {sender.full_name} ({sender.primary_upi}).",
                notif_type=NotificationType.MONEY_RECEIVED,
                reference_id=ref_no
            )

        # Audit Logging
        log_audit(
            action="PAYMENT_SUCCESS",
            user_id=sender.id,
            user_email=sender.email,
            entity_type="TRANSACTION",
            entity_id=ref_no,
            result="SUCCESS",
            details={
                "amount": amount,
                "receiver_upi": receiver_upi,
                "risk_score": risk_score,
                "risk_level": risk_level,
            }
        )

        # Dispatch n8n payment success webhook
        dispatch_event("PAYMENT_SUCCESS", {
            "reference_no": ref_no,
            "sender_email": sender.email,
            "receiver_upi": receiver_upi,
            "amount": amount,
            "category": txn.category,
            "risk_score": risk_score,
        })

        return True, "Payment completed successfully.", txn

    except Exception as e:
        db.session.rollback()
        logger.error(f"Transaction execution failed: {e}")

        # Record failure transaction if possible
        try:
            failed_txn = Transaction(
                reference_no=ref_no,
                sender_id=sender.id,
                receiver_id=receiver_user.id if receiver_user else None,
                sender_upi=sender.primary_upi,
                receiver_upi=receiver_upi,
                amount=amount,
                type=txn_type,
                status=TransactionStatus.FAILED,
                description=description,
                failure_reason=str(e),
                risk_score=risk_score,
                risk_level=risk_level,
            )
            db.session.add(failed_txn)
            db.session.commit()

            create_notification(
                user_id=sender.id,
                title="Payment Failed",
                message=f"Simulated payment of {format_currency(amount)} to {receiver_upi} failed.",
                notif_type=NotificationType.PAYMENT_FAILED,
                reference_id=ref_no
            )

            dispatch_event("PAYMENT_FAILURE", {
                "reference_no": ref_no,
                "sender_email": sender.email,
                "receiver_upi": receiver_upi,
                "amount": amount,
                "error": str(e),
            })
        except Exception:
            pass

        return False, "Simulated payment processing error. Please try again.", None
