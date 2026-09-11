from app.models.user import User
from app.models.transaction import Transaction, TransactionStatus, RiskLevel
from app.services.payment_service import execute_simulated_transfer
from app.services.risk_service import calculate_simulated_risk


def test_successful_simulated_transfer(app, test_user, test_receiver):
    with app.app_context():
        sender = User.query.get(test_user)
        receiver = User.query.get(test_receiver)

        success, msg, txn = execute_simulated_transfer(
            sender=sender,
            receiver_upi="receiver@jaganpay",
            amount=5000.0,
            description="Unit Test Payment",
        )
        assert success is True
        assert txn is not None
        assert txn.status == TransactionStatus.SUCCESS
        assert txn.reference_no.startswith("JGP")

        # Check balances
        sender_acc = sender.bank_accounts.first()
        receiver_acc = receiver.bank_accounts.first()

        assert sender_acc.demo_balance == 20000.0
        assert receiver_acc.demo_balance == 15000.0


def test_insufficient_demo_balance(app, test_user, test_receiver):
    with app.app_context():
        sender = User.query.get(test_user)
        # Transfer more than available balance
        success, msg, txn = execute_simulated_transfer(
            sender=sender,
            receiver_upi="receiver@jaganpay",
            amount=99999.0,
        )
        assert success is False
        assert "insufficient" in msg.lower()

        # Balance remains unchanged
        assert sender.bank_accounts.first().demo_balance == 25000.0


def test_cannot_transfer_to_self(app, test_user):
    with app.app_context():
        sender = User.query.get(test_user)
        success, msg, txn = execute_simulated_transfer(
            sender=sender,
            receiver_upi=sender.primary_upi,
            amount=100.0,
        )
        assert success is False
        assert "own upi" in msg.lower()


def test_risk_scoring_engine(app, test_user):
    with app.app_context():
        # Normal small amount to existing/normal recipient
        score, level, factors = calculate_simulated_risk(test_user, "someone@jaganpay", 250.0)
        assert level in [RiskLevel.LOW, RiskLevel.MEDIUM]

        # Very large transfer (> ₹50,000)
        high_score, high_level, high_factors = calculate_simulated_risk(test_user, "newstranger@jaganpay", 60000.0)
        assert high_score >= 60
        assert any("50,000" in f for f in high_factors)
