from datetime import datetime
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.middleware.auth_guard import verified_required
from app.models.transaction import Transaction, TransactionStatus
from app.models.bank_account import DemoBankAccount
from app.models.notification import Notification
from app.ai.gemini_service import ai_service

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
@verified_required
def index():
    # Greeting based on local hour
    hour = datetime.utcnow().hour
    # Approximation for IST (+5:30)
    ist_hour = (hour + 5) % 24
    if ist_hour < 12:
        greeting = "Good morning"
    elif ist_hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    # User's demo bank accounts
    accounts = current_user.bank_accounts.all()
    primary_acc = next((acc for acc in accounts if acc.is_primary), accounts[0] if accounts else None)

    # Recent transactions (last 6)
    recent_txns = Transaction.query.filter(
        (Transaction.sender_id == current_user.id) | (Transaction.receiver_id == current_user.id)
    ).order_by(Transaction.created_at.desc()).limit(6).all()

    # Calculate month spent and income
    sent_txns = Transaction.query.filter(
        Transaction.sender_id == current_user.id,
        Transaction.status == TransactionStatus.SUCCESS
    ).all()
    total_spent = sum(t.amount for t in sent_txns)

    received_txns = Transaction.query.filter(
        Transaction.receiver_id == current_user.id,
        Transaction.status == TransactionStatus.SUCCESS
    ).all()
    total_received = sum(t.amount for t in received_txns)

    # Quick AI insight
    context_data = {
        "name": current_user.full_name,
        "balance": current_user.total_demo_balance,
        "spent": total_spent,
        "top_category": "Dining / Food" if total_spent > 0 else "None",
    }
    ai_quick_tip = ai_service.ask_ai("Give me a 1-sentence smart spending tip for my dashboard", context_data)

    # Recent notifications
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.created_at.desc()).limit(4).all()

    return render_template(
        "dashboard/index.html",
        user=current_user,
        greeting=greeting,
        accounts=accounts,
        primary_acc=primary_acc,
        recent_txns=recent_txns,
        total_spent=total_spent,
        total_received=total_received,
        ai_quick_tip=ai_quick_tip,
        notifications=notifications,
    )
