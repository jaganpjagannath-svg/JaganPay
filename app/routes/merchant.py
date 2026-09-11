from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.middleware.auth_guard import verified_required
from app.models.merchant import Merchant
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.models.user import Role
from app.services.qr_service import build_upi_string, generate_qr_base64
from app.services.payment_service import execute_simulated_transfer
from app.services.audit_service import log_audit

merchant_bp = Blueprint("merchant", __name__)


@merchant_bp.route("/merchant")
@login_required
@verified_required
def dashboard():
    merchant = current_user.merchant_profile

    # If user doesn't have a merchant profile, give option to create demo merchant
    if not merchant:
        return render_template("merchant/register.html")

    # Fetch merchant received payments
    payments = Transaction.query.filter_by(
        receiver_id=current_user.id
    ).order_by(Transaction.created_at.desc()).all()

    total_sales = sum(p.amount for p in payments if p.status == TransactionStatus.SUCCESS)

    # Today's sales
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_sales = sum(
        p.amount for p in payments
        if p.status == TransactionStatus.SUCCESS and p.created_at >= today_start
    )

    # Generate Merchant QR code
    upi_str = build_upi_string(merchant.demo_upi_id, merchant.business_name, note="Store Payment")
    qr_code_base64 = generate_qr_base64(upi_str)

    return render_template(
        "merchant/dashboard.html",
        merchant=merchant,
        payments=payments[:10],
        total_sales=total_sales,
        today_sales=today_sales,
        sales_count=len(payments),
        qr_code_base64=qr_code_base64,
        upi_string=upi_str,
    )


@merchant_bp.route("/merchant/register", methods=["POST"])
@login_required
@verified_required
def register_merchant():
    biz_name = request.form.get("business_name", "").strip()
    category = request.form.get("category", "Retail").strip()
    location = request.form.get("location", "Tech Park Plaza").strip()

    if not biz_name:
        flash("Please enter your business name.", "danger")
        return redirect(url_for("merchant.dashboard"))

    clean_code = "".join(filter(str.isalnum, biz_name)).lower()
    merchant_code = f"MERCH-{clean_code[:10].upper()}"
    demo_upi = f"{clean_code[:12]}@jaganpay"

    merchant = Merchant(
        user_id=current_user.id,
        business_name=biz_name,
        merchant_code=merchant_code,
        demo_upi_id=demo_upi,
        category=category,
        location=location,
        status="ACTIVE",
    )
    current_user.role = Role.MERCHANT
    db.session.add(merchant)
    db.session.commit()

    log_audit("MERCHANT_REGISTERED", current_user.id, current_user.email, "MERCHANT", merchant_code, "SUCCESS")
    flash(f"Merchant profile created for {biz_name}! Your merchant UPI is {demo_upi}.", "success")
    return redirect(url_for("merchant.dashboard"))


@merchant_bp.route("/merchant/refund-simulation", methods=["POST"])
@login_required
@verified_required
def simulate_refund():
    txn_ref = request.form.get("reference_no", "").strip()
    original_txn = Transaction.query.filter_by(reference_no=txn_ref).first()

    if not original_txn:
        flash("Transaction not found for refund simulation.", "danger")
        return redirect(url_for("merchant.dashboard"))

    if original_txn.receiver_id != current_user.id:
        flash("You can only refund transactions received by your merchant account.", "danger")
        return redirect(url_for("merchant.dashboard"))

    original_txn.status = TransactionStatus.REFUNDED
    db.session.commit()

    log_audit("REFUND_SIMULATED", current_user.id, current_user.email, "TRANSACTION", txn_ref, "SUCCESS")
    flash(f"Simulated refund processed successfully for {original_txn.reference_no}!", "info")
    return redirect(url_for("merchant.dashboard"))
