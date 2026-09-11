from datetime import datetime, timedelta
from app.models.transaction import Transaction, RiskLevel, TransactionStatus


def calculate_simulated_risk(sender_id: str, receiver_upi: str, amount: float) -> tuple[int, str, list[str]]:
    """
    Simulated educational fraud/risk scoring engine (0-100).
    Evaluates simulated transaction patterns without real-world fraud claims.
    """
    score = 10  # Baseline safe score
    factors = []

    # 1. Amount threshold checks
    if amount >= 50000:
        score += 45
        factors.append("Very large simulated transfer (> ₹50,000)")
    elif amount >= 15000:
        score += 25
        factors.append("Substantial simulated transfer (> ₹15,000)")
    elif amount <= 10:
        score += 5
        factors.append("Micro test amount transfer")

    # 2. Transaction velocity (transactions in the last 10 minutes)
    ten_mins_ago = datetime.utcnow() - timedelta(minutes=10)
    recent_count = Transaction.query.filter(
        Transaction.sender_id == sender_id,
        Transaction.created_at >= ten_mins_ago
    ).count()

    if recent_count >= 4:
        score += 35
        factors.append(f"High velocity: {recent_count} transactions initiated within 10 minutes")
    elif recent_count >= 2:
        score += 15
        factors.append(f"Moderate velocity: {recent_count} transactions in last 10 minutes")

    # 3. New Recipient Check (Has sender paid this UPI ID before?)
    previous_txn = Transaction.query.filter_by(
        sender_id=sender_id,
        receiver_upi=receiver_upi,
        status=TransactionStatus.SUCCESS
    ).first()

    if not previous_txn:
        score += 15
        factors.append("First-time transaction to this demo UPI ID")

    # 4. Unusual transaction timing (Midnight to 5 AM)
    current_hour = datetime.utcnow().hour
    if 1 <= current_hour <= 4:
        score += 15
        factors.append("Off-peak simulated transaction hour (01:00 - 04:00 UTC)")

    # 5. Recent failed transactions
    recent_failed = Transaction.query.filter(
        Transaction.sender_id == sender_id,
        Transaction.status == TransactionStatus.FAILED,
        Transaction.created_at >= datetime.utcnow() - timedelta(minutes=30)
    ).count()

    if recent_failed >= 2:
        score += 25
        factors.append(f"{recent_failed} failed attempts recorded in the last 30 minutes")

    # Cap score at 99
    score = min(score, 99)

    # Determine risk level
    if score >= 65:
        level = RiskLevel.HIGH
    elif score >= 35:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.LOW

    return score, level, factors
