import json
from collections import defaultdict
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.middleware.auth_guard import verified_required
from app.models.transaction import Transaction, TransactionStatus, SpendingCategory
from app.ai.gemini_service import ai_service

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/analytics")
@login_required
@verified_required
def index():
    # Fetch all completed debit transactions
    debits = Transaction.query.filter_by(
        sender_id=current_user.id,
        status=TransactionStatus.SUCCESS
    ).all()

    # Fetch all completed credit transactions
    credits = Transaction.query.filter_by(
        receiver_id=current_user.id,
        status=TransactionStatus.SUCCESS
    ).all()

    total_spent = sum(t.amount for t in debits)
    total_received = sum(t.amount for t in credits)
    net_flow = total_received - total_spent

    largest_txn = max((t.amount for t in debits), default=0.0)
    avg_txn = (total_spent / len(debits)) if debits else 0.0
    txn_count = len(debits)

    # Category breakdown
    category_totals = defaultdict(float)
    for cat in SpendingCategory.ALL:
        category_totals[cat] = 0.0

    for t in debits:
        cat = t.category if t.category in SpendingCategory.ALL else SpendingCategory.OTHER
        category_totals[cat] += t.amount

    # Top category
    top_category = max(category_totals.items(), key=lambda x: x[1])[0] if total_spent > 0 else "None"

    # Category breakdown summary text for AI
    breakdown_lines = [f"- {k}: ₹{v:,.2f}" for k, v in category_totals.items() if v > 0]
    breakdown_text = "\n".join(breakdown_lines) if breakdown_lines else "No categorized expenditure yet."

    metrics = {
        "total_spent": total_spent,
        "total_received": total_received,
        "net_flow": net_flow,
        "top_category": top_category,
        "largest_txn": largest_txn,
        "avg_txn": avg_txn,
        "txn_count": txn_count,
        "breakdown_text": breakdown_text,
    }

    ai_insight = ai_service.generate_spending_insights(metrics)

    # Prepare data for Chart.js
    chart_categories = list(category_totals.keys())
    chart_values = [round(category_totals[k], 2) for k in chart_categories]

    return render_template(
        "analytics/index.html",
        metrics=metrics,
        ai_insight=ai_insight,
        chart_categories=json.dumps(chart_categories),
        chart_values=json.dumps(chart_values),
    )
