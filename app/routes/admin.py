from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.middleware.auth_guard import admin_required
from app.models.user import User, Role
from app.models.transaction import Transaction, TransactionStatus, RiskLevel
from app.models.merchant import Merchant
from app.models.security import SecurityEvent, AuditLog, RiskAlert
from app.models.support import SupportTicket, TicketStatus
from app.models.otp import OTPVerification
from app.services.audit_service import log_audit
from app.services.webhook_service import dispatch_event

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@login_required
@admin_required
def index():
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_txns = Transaction.query.count()
    successful_txns = Transaction.query.filter_by(status=TransactionStatus.SUCCESS).count()
    failed_txns = Transaction.query.filter_by(status=TransactionStatus.FAILED).count()

    # Total simulated volume
    all_success = Transaction.query.filter_by(status=TransactionStatus.SUCCESS).all()
    total_volume = sum(t.amount for t in all_success)

    high_risk_alerts = RiskAlert.query.filter_by(status="PENDING_REVIEW").count()
    open_tickets = SupportTicket.query.filter_by(status=TicketStatus.OPEN).count()
    active_merchants = Merchant.query.filter_by(status="ACTIVE").count()

    recent_txns = Transaction.query.order_by(Transaction.created_at.desc()).limit(8).all()
    recent_alerts = RiskAlert.query.order_by(RiskAlert.created_at.desc()).limit(5).all()

    return render_template(
        "admin/index.html",
        total_users=total_users,
        active_users=active_users,
        total_txns=total_txns,
        successful_txns=successful_txns,
        failed_txns=failed_txns,
        total_volume=total_volume,
        high_risk_alerts=high_risk_alerts,
        open_tickets=open_tickets,
        active_merchants=active_merchants,
        recent_txns=recent_txns,
        recent_alerts=recent_alerts,
    )


@admin_bp.route("/users")
@login_required
@admin_required
def users():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "").strip()

    query = User.query
    if search:
        query = query.filter(
            (User.full_name.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%")) |
            (User.phone.ilike(f"%{search}%"))
        )

    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    return render_template("admin/users.html", users=pagination.items, pagination=pagination, search=search)


@admin_bp.route("/users/<user_id>/toggle-status", methods=["POST"])
@login_required
@admin_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot suspend your own admin account.", "danger")
        return redirect(url_for("admin.users"))

    user.is_active = not user.is_active
    db.session.commit()

    status_str = "activated" if user.is_active else "suspended"
    log_audit("USER_STATUS_TOGGLE", current_user.id, current_user.email, "USER", user.id, "SUCCESS", {"status": status_str})
    flash(f"User {user.full_name} has been {status_str}.", "info")
    return redirect(url_for("admin.users"))


@admin_bp.route("/transactions")
@login_required
@admin_required
def transactions():
    page = request.args.get("page", 1, type=int)
    status_filter = request.args.get("status", "all")

    query = Transaction.query
    if status_filter != "all":
        query = query.filter_by(status=status_filter.upper())

    pagination = query.order_by(Transaction.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    return render_template("admin/transactions.html", transactions=pagination.items, pagination=pagination, current_status=status_filter)


@admin_bp.route("/risk")
@login_required
@admin_required
def risk_alerts():
    alerts = RiskAlert.query.order_by(RiskAlert.created_at.desc()).all()
    return render_template("admin/risk_alerts.html", alerts=alerts)


@admin_bp.route("/risk/<int:alert_id>/action", methods=["POST"])
@login_required
@admin_required
def handle_risk_alert(alert_id):
    action = request.form.get("action")  # 'dismiss' or 'action_taken'
    notes = request.form.get("admin_notes", "").strip()
    alert = RiskAlert.query.get_or_404(alert_id)

    alert.status = "DISMISSED" if action == "dismiss" else "ACTION_TAKEN"
    alert.admin_notes = notes
    db.session.commit()

    log_audit("RISK_ALERT_RESOLVED", current_user.id, current_user.email, "RISK_ALERT", str(alert.id), "SUCCESS", {"action": alert.status})
    flash(f"Risk Alert #{alert.id} marked as {alert.status}.", "success")
    return redirect(url_for("admin.risk_alerts"))


@admin_bp.route("/merchants")
@login_required
@admin_required
def merchants():
    merchants_list = Merchant.query.order_by(Merchant.created_at.desc()).all()
    return render_template("admin/merchants.html", merchants=merchants_list)


@admin_bp.route("/support")
@login_required
@admin_required
def support():
    tickets = SupportTicket.query.order_by(SupportTicket.created_at.desc()).all()
    return render_template("admin/support.html", tickets=tickets)


@admin_bp.route("/audit-logs")
@login_required
@admin_required
def audit_logs():
    page = request.args.get("page", 1, type=int)
    pagination = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template("admin/audit_logs.html", logs=pagination.items, pagination=pagination)


@admin_bp.route("/automation")
@login_required
@admin_required
def automation():
    webhooks = current_app.config.get("N8N_WEBHOOKS", {})
    return render_template("admin/automation.html", webhooks=webhooks)


@admin_bp.route("/automation/test-trigger", methods=["POST"])
@login_required
@admin_required
def test_automation():
    event_type = request.form.get("event_type", "ADMIN_REPORT")
    dispatch_event(event_type, {
        "triggered_by": current_user.email,
        "sample_metric": "Demo Ping Test",
        "timestamp": datetime.utcnow().isoformat(),
    })
    flash(f"Dispatched test webhook event '{event_type}' to n8n.", "success")
    return redirect(url_for("admin.automation"))


@admin_bp.route("/system-health")
@login_required
@admin_required
def system_health():
    import sys
    import platform

    db_ok = True
    try:
        db.session.execute(db.text("SELECT 1"))
    except Exception:
        db_ok = False

    ai_configured = bool(current_app.config.get("GEMINI_API_KEY"))

    health_info = {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "database_connected": db_ok,
        "ai_configured": ai_configured,
        "demo_mode": current_app.config.get("DEMO_MODE", True),
        "total_users": User.query.count(),
        "total_transactions": Transaction.query.count(),
        "n8n_base_url": current_app.config.get("N8N_BASE_URL"),
    }
    return render_template("admin/system_health.html", health=health_info)
