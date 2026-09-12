from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.middleware.auth_guard import verified_required
from app.models.transaction import Transaction, TransactionStatus, TransactionType, SpendingCategory
from app.models.bank_account import DemoBankAccount
from app.models.notification import Notification
from app.ai.gemini_service import ai_service
from app.services.payment_service import execute_simulated_transfer

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

    # Transaction count & allocation limit
    txn_count = len(sent_txns) + len(received_txns)
    allocation_limit = 50000.0

    # Nearby merchants for the interactive local map section (matching reference image)
    nearby_merchants = [
        {
            "name": "Coffee Club & Bistro",
            "category": "Cafe & Dining",
            "distance": "0.2 km",
            "upi_id": "coffeeclub@jaganpay",
            "avatar": "☕",
            "color": "from-amber-600 to-orange-600",
            "rating": "4.8"
        },
        {
            "name": "Apollo Super Pharmacy",
            "category": "Healthcare & Meds",
            "distance": "0.8 km",
            "upi_id": "apollopharmacy@jaganpay",
            "avatar": "💊",
            "color": "from-emerald-600 to-teal-600",
            "rating": "4.9"
        },
        {
            "name": "DMart Express Supermarket",
            "category": "Daily Grocery",
            "distance": "1.4 km",
            "upi_id": "dmartexpress@jaganpay",
            "avatar": "🛒",
            "color": "from-blue-600 to-cyan-600",
            "rating": "4.7"
        },
    ]

    # Quick 6-Month Transaction Analytics Bar Chart Data (matching reference image)
    chart_months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    base_spent = round(total_spent, 2)
    chart_spent = [1450.0, 3200.0, 2100.0, 4800.0, 8900.0, max(base_spent, 1650.0)]

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
        txn_count=txn_count,
        allocation_limit=allocation_limit,
        nearby_merchants=nearby_merchants,
        chart_months=chart_months,
        chart_spent=chart_spent,
        ai_quick_tip=ai_quick_tip,
        notifications=notifications,
    )


@dashboard_bp.route("/dashboard/add-demo-funds", methods=["POST"])
@login_required
@verified_required
def add_demo_funds():
    try:
        amount = float(request.form.get("amount", 5000))
    except (ValueError, TypeError):
        amount = 5000.0

    if amount <= 0 or amount > 500000:
        flash("Simulated amount must be between ₹100 and ₹5,00,000", "warning")
        return redirect(url_for("dashboard.index"))

    primary_acc = DemoBankAccount.query.filter_by(user_id=current_user.id, is_primary=True).first()
    if not primary_acc:
        primary_acc = DemoBankAccount.query.filter_by(user_id=current_user.id).first()

    if primary_acc:
        primary_acc.demo_balance += amount
        db.session.commit()
        flash(f"Successfully credited ₹{amount:,.2f} demo money to your simulated account!", "success")
    else:
        flash("No demo bank account found to credit funds.", "danger")

    return redirect(url_for("dashboard.index"))


@dashboard_bp.route("/dashboard/pay-utility", methods=["POST"])
@login_required
@verified_required
def pay_utility():
    utility_name = request.form.get("utility_name", "Electricity").strip()
    consumer_id = request.form.get("consumer_id", "DEMO998877").strip()
    try:
        amount = float(request.form.get("amount", 450))
    except (ValueError, TypeError):
        amount = 450.0

    if amount <= 0:
        flash("Invalid bill amount entered.", "warning")
        return redirect(url_for("dashboard.index"))

    # Map to utility demo merchant
    utility_upis = {
        "Electricity": "powercorp@jaganpay",
        "Mobile Recharge": "airtel.demo@jaganpay",
        "DTH / Cable": "tataplay.demo@jaganpay",
        "FASTag": "fastag.toll@jaganpay",
        "Credit Card": "cardbill@jaganpay",
        "Water": "municipalwater@jaganpay",
        "LPG Gas": "indane.gas@jaganpay",
        "Broadband": "fiberbroadband@jaganpay",
    }
    receiver_upi = utility_upis.get(utility_name, "bills@jaganpay")

    success, msg, txn = execute_simulated_transfer(
        sender=current_user,
        receiver_upi=receiver_upi,
        amount=amount,
        description=f"{utility_name} Payment #{consumer_id}",
        category=SpendingCategory.BILLS,
        txn_type=TransactionType.RECHARGE_SIMULATION,
    )

    if success:
        flash(f"Simulated {utility_name} bill of ₹{amount:,.2f} paid successfully! Ref: {txn.reference_no}", "success")
    else:
        flash(f"Bill payment failed: {msg}", "danger")

    return redirect(url_for("dashboard.index"))
