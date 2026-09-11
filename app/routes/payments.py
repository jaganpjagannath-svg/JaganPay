import urllib.parse
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.middleware.auth_guard import verified_required
from app.models.bank_account import DemoBankAccount, UPIProfile
from app.models.transaction import (
    Transaction, PaymentRequest, TransactionType, TransactionStatus, SpendingCategory
)
from app.models.otp import OTPPurpose
from app.models.notification import NotificationType
from app.services.payment_service import execute_simulated_transfer
from app.services.auth_service import request_otp, verify_user_otp
from app.services.qr_service import build_upi_string, generate_qr_base64
from app.services.notification_service import create_notification
from app.utils.validators import validate_upi_id
from app.utils.helpers import format_currency

payments_bp = Blueprint("payments", __name__)


@payments_bp.route("/send-money", methods=["GET", "POST"])
@login_required
@verified_required
def send_money():
    accounts = current_user.bank_accounts.all()
    categories = SpendingCategory.ALL

    # Pre-fill from query params if redirected from QR or Payment Request
    prefill_upi = request.args.get("upi", "")
    prefill_amount = request.args.get("amount", "")
    prefill_desc = request.args.get("desc", "")

    if request.method == "POST":
        receiver_upi = request.form.get("receiver_upi", "").strip()
        try:
            amount = float(request.form.get("amount", 0))
        except ValueError:
            amount = 0.0

        description = request.form.get("description", "Demo Transfer").strip()
        category = request.form.get("category", SpendingCategory.OTHER)
        account_id = request.form.get("account_id", type=int)
        pin = request.form.get("demo_pin", "").strip()
        otp = request.form.get("otp", "").strip()

        # Validations
        if not validate_upi_id(receiver_upi):
            flash("Invalid UPI ID format. Example: user@jaganpay", "danger")
            return render_template("payments/send.html", accounts=accounts, categories=categories, prefill_upi=receiver_upi, prefill_amount=amount)

        if amount <= 0:
            flash("Please enter a valid transfer amount greater than ₹0.", "danger")
            return render_template("payments/send.html", accounts=accounts, categories=categories, prefill_upi=receiver_upi, prefill_amount=amount)

        # Verify Demo PIN
        if not current_user.check_pin(pin):
            flash("Incorrect Demo PIN. Default PIN for demo accounts is 1234.", "danger")
            return render_template("payments/send.html", accounts=accounts, categories=categories, prefill_upi=receiver_upi, prefill_amount=amount)

        # Sensitive Transfer Extra Verification Check
        threshold = current_app.config.get("SENSITIVE_TRANSACTION_THRESHOLD", 10000.0)
        if amount >= threshold:
            # Check if OTP was provided and is valid
            if not otp:
                # Issue OTP and request user to input it
                request_otp(current_user, purpose=OTPPurpose.SENSITIVE_ACTION)
                flash(f"Large simulated transfer (≥ {format_currency(threshold)}) requires OTP verification. A security code was dispatched.", "warning")
                return render_template(
                    "payments/send.html",
                    accounts=accounts,
                    categories=categories,
                    prefill_upi=receiver_upi,
                    prefill_amount=amount,
                    prefill_desc=description,
                    require_otp=True,
                )
            else:
                otp_valid, otp_msg = verify_user_otp(current_user, otp, purpose=OTPPurpose.SENSITIVE_ACTION)
                if not otp_valid:
                    flash(f"Sensitive Action OTP Verification failed: {otp_msg}", "danger")
                    return render_template(
                        "payments/send.html",
                        accounts=accounts,
                        categories=categories,
                        prefill_upi=receiver_upi,
                        prefill_amount=amount,
                        prefill_desc=description,
                        require_otp=True
                    )

        # Execute simulated payment
        success, message, txn = execute_simulated_transfer(
            sender=current_user,
            receiver_upi=receiver_upi,
            amount=amount,
            description=description,
            category=category,
            txn_type=TransactionType.SEND,
            account_id=account_id,
        )

        if success and txn:
            flash(f"Simulated payment of {format_currency(amount)} to {receiver_upi} was successful!", "success")
            return redirect(url_for("transactions.receipt", txn_id=txn.id))
        else:
            flash(message, "danger")

    return render_template(
        "payments/send.html",
        accounts=accounts,
        categories=categories,
        prefill_upi=prefill_upi,
        prefill_amount=prefill_amount,
        prefill_desc=prefill_desc,
        require_otp=False
    )


@payments_bp.route("/receive-money", methods=["GET", "POST"])
@login_required
@verified_required
def receive_money():
    upi_id = current_user.primary_upi
    amount = request.args.get("amount", type=float)
    note = request.args.get("note", "Demo Payment")

    upi_string = build_upi_string(upi_id, current_user.full_name, amount, note)
    qr_code_base64 = generate_qr_base64(upi_string)

    return render_template(
        "payments/receive.html",
        upi_id=upi_id,
        user=current_user,
        amount=amount,
        note=note,
        upi_string=upi_string,
        qr_code_base64=qr_code_base64
    )


@payments_bp.route("/request-money", methods=["GET", "POST"])
@login_required
@verified_required
def request_money():
    if request.method == "POST":
        payer_upi = request.form.get("payer_upi", "").strip()
        try:
            amount = float(request.form.get("amount", 0))
        except ValueError:
            amount = 0.0
        description = request.form.get("description", "Demo Payment Request").strip()

        if not validate_upi_id(payer_upi):
            flash("Invalid payer UPI ID.", "danger")
            return redirect(url_for("payments.request_money"))

        if amount <= 0:
            flash("Amount must be greater than zero.", "danger")
            return redirect(url_for("payments.request_money"))

        req = PaymentRequest(
            requester_id=current_user.id,
            payer_upi=payer_upi,
            amount=amount,
            description=description,
            status="PENDING",
            expires_at=datetime.utcnow() + timedelta(days=3),
        )
        db.session.add(req)
        db.session.commit()

        # Try to find receiver to notify them
        payer_profile = UPIProfile.query.filter_by(upi_id=payer_upi).first()
        if payer_profile and payer_profile.user:
            create_notification(
                user_id=payer_profile.user.id,
                title="Payment Request Received",
                message=f"{current_user.full_name} requested {format_currency(amount)} for '{description}'.",
                notif_type=NotificationType.PAYMENT_REQUEST,
                reference_id=req.id
            )

        flash(f"Payment request for {format_currency(amount)} sent to {payer_upi}.", "success")
        return redirect(url_for("payments.request_money"))

    # List incoming and outgoing requests
    my_upi = current_user.primary_upi
    incoming_requests = PaymentRequest.query.filter_by(payer_upi=my_upi, status="PENDING").order_by(PaymentRequest.created_at.desc()).all()
    outgoing_requests = PaymentRequest.query.filter_by(requester_id=current_user.id).order_by(PaymentRequest.created_at.desc()).all()

    return render_template(
        "payments/request.html",
        incoming_requests=incoming_requests,
        outgoing_requests=outgoing_requests
    )


@payments_bp.route("/request-money/<req_id>/action", methods=["POST"])
@login_required
@verified_required
def handle_request_action(req_id):
    action = request.form.get("action")  # 'pay' or 'reject'
    req = PaymentRequest.query.get_or_404(req_id)

    if req.payer_upi.lower() != current_user.primary_upi.lower():
        flash("You are not authorized to respond to this request.", "danger")
        return redirect(url_for("payments.request_money"))

    if action == "pay":
        # Redirect to send money pre-filled
        req.status = "PAID"
        db.session.commit()
        return redirect(url_for("payments.send_money", upi=req.requester.primary_upi, amount=req.amount, desc=req.description))
    elif action == "reject":
        req.status = "REJECTED"
        db.session.commit()
        flash("Payment request declined.", "info")

    return redirect(url_for("payments.request_money"))


@payments_bp.route("/qr-payment", methods=["GET", "POST"])
@login_required
@verified_required
def qr_payment():
    if request.method == "POST":
        raw_qr_payload = request.form.get("qr_payload", "").strip()

        # Parse UPI URI if provided (e.g. upi://pay?pa=...&pn=...&am=...)
        if raw_qr_payload.startswith("upi://pay"):
            parsed = urllib.parse.urlparse(raw_qr_payload)
            params = urllib.parse.parse_qs(parsed.query)
            pa = params.get("pa", [""])[0]
            am = params.get("am", [""])[0]
            tn = params.get("tn", [""])[0]
            return redirect(url_for("payments.send_money", upi=pa, amount=am, desc=tn))
        elif validate_upi_id(raw_qr_payload):
            return redirect(url_for("payments.send_money", upi=raw_qr_payload))
        else:
            flash("Invalid UPI QR code or text payload.", "danger")

    return render_template("payments/qr_pay.html")
