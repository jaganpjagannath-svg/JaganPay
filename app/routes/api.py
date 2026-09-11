import re
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session, current_app
from flask_login import login_user, logout_user, current_user, login_required
from app.extensions import db, limiter
from app.models.user import User, Role
from app.models.otp import OTPPurpose, OTPVerification, OTPChallenge, OTPChannel
from app.models.bank_account import DemoBankAccount, UPIProfile, BankNames
from app.models.transaction import Transaction, PaymentRequest, TransactionType, TransactionStatus, SpendingCategory
from app.models.notification import Notification, NotificationType
from app.models.security import SecurityEvent, AuditLog, RiskAlert
from app.models.support import SupportTicket, SupportMessage, TicketStatus, TicketPriority
from app.services.auth_service import request_otp, verify_user_otp
from app.services.otp_service import OTPService, get_latest_mock_sms
from app.services.payment_service import execute_simulated_transfer
from app.services.risk_service import calculate_simulated_risk
from app.services.qr_service import build_upi_string, generate_qr_base64
from app.services.webhook_service import dispatch_event
from app.services.audit_service import log_audit, log_security_event
from app.ai.gemini_service import ai_service
from app.utils.validators import validate_email, validate_phone, validate_upi_id, validate_password_strength

api_bp = Blueprint("api", __name__)


# ----------------------------------------------------
# AUTHENTICATION APIS
# ----------------------------------------------------

@api_bp.route("/auth/register", methods=["POST"])
@limiter.limit("20 per hour")
def api_register():
    data = request.get_json() or {}
    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip().lower()
    phone = data.get("phone", "").strip()
    password = data.get("password", "")

    if not full_name or not validate_email(email) or not validate_phone(phone):
        return jsonify({"success": False, "message": "Invalid registration input.", "error_code": "INVALID_INPUT"}), 400

    is_valid_pw, pw_msg = validate_password_strength(password)
    if not is_valid_pw:
        return jsonify({"success": False, "message": pw_msg, "error_code": "WEAK_PASSWORD"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": "Email already registered.", "error_code": "EMAIL_EXISTS"}), 409

    user = User(full_name=full_name, email=email, phone=phone, role=Role.USER, is_verified=False)
    user.set_password(password)
    user.set_pin("1234")
    db.session.add(user)
    db.session.commit()

    # Generate UPI & Demo Bank Account
    handle = re.sub(r"[^a-zA-Z0-9]", "", email.split("@")[0]).lower()
    upi_profile = UPIProfile(
        user_id=user.id,
        upi_id=f"{handle}@jaganpay",
        qr_data=f"upi://pay?pa={handle}@jaganpay&pn={user.full_name}&cu=INR&mode=02",
    )
    db.session.add(upi_profile)

    demo_acc = DemoBankAccount(
        user_id=user.id,
        bank_name=BankNames.JAGAN_BANK,
        account_holder=user.full_name,
        account_number_masked=f"•••• •••• {phone[-4:] if len(phone) >= 4 else '1001'}",
        demo_balance=25000.0,
        is_primary=True,
    )
    db.session.add(demo_acc)
    db.session.commit()

    # Dispatch OTP via SMS provider
    request_otp(user, purpose=OTPPurpose.REGISTRATION, channel=OTPChannel.SMS)

    return jsonify({
        "success": True,
        "message": "User registered. Verification OTP dispatched.",
        "data": {
            "user_id": user.id,
            "email": user.email,
        }
    }), 201


@api_bp.route("/auth/send-otp", methods=["POST"])
@limiter.limit("30 per hour")
def api_send_otp():
    data = request.get_json() or {}
    identifier = data.get("identifier", "").strip()
    channel = data.get("channel", "").strip().upper()
    purpose = data.get("purpose", "").strip().upper() or OTPPurpose.REGISTRATION

    if not identifier:
        return jsonify({"success": False, "message": "identifier is required.", "error_code": "MISSING_IDENTIFIER"}), 400

    if not channel:
        channel = OTPChannel.EMAIL if "@" in identifier else OTPChannel.SMS

    # Check if this identifier corresponds to an existing user
    user = User.query.filter(
        (User.phone == identifier) | (User.email == identifier.lower())
    ).first()
    user_id = user.id if user else None

    try:
        challenge, expires_in = OTPService.create_challenge(
            identifier=identifier,
            channel=channel,
            purpose=purpose,
            user_id=user_id
        )
        return jsonify({
            "success": True,
            "message": "OTP sent successfully",
            "otp_required": True,
            "expires_in": expires_in
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": "Failed to send OTP.", "error_code": "OTP_SEND_FAILED"}), 500


@api_bp.route("/auth/verify-otp", methods=["POST"])
@limiter.limit("60 per hour")
def api_verify_otp():
    data = request.get_json() or {}
    identifier = data.get("identifier", "").strip()
    user_id = data.get("user_id") or (current_user.id if current_user.is_authenticated else None)
    otp_code = data.get("otp", "").strip()
    purpose = data.get("purpose", "").strip().upper() or None

    if not otp_code or (not identifier and not user_id):
        return jsonify({
            "success": False,
            "message": "identifier (or user_id) and otp are required.",
            "error_code": "MISSING_FIELDS"
        }), 400

    user = None
    if user_id:
        user = User.query.get(user_id)
        if not identifier and user:
            identifier = user.phone or user.email
    elif identifier:
        user = User.query.filter(
            (User.phone == identifier) | (User.email == identifier.lower())
        ).first()

    success, msg, challenge = OTPService.verify_challenge(
        raw_code=otp_code,
        identifier=identifier,
        purpose=purpose,
        user_id=user.id if user else user_id
    )

    if success:
        if user:
            login_user(user)
        resp = {
            "success": True,
            "message": "OTP verified successfully"
        }
        if user:
            resp["data"] = user.to_dict()
        return jsonify(resp), 200
    else:
        return jsonify({"success": False, "message": msg, "error_code": "OTP_INVALID"}), 400


@api_bp.route("/auth/resend-otp", methods=["POST"])
@limiter.limit("20 per hour")
def api_resend_otp():
    data = request.get_json() or {}
    identifier = data.get("identifier", "").strip()
    purpose = data.get("purpose", "").strip().upper() or OTPPurpose.REGISTRATION

    if not identifier:
        if current_user.is_authenticated:
            identifier = current_user.phone or current_user.email
        else:
            return jsonify({"success": False, "message": "identifier is required.", "error_code": "MISSING_IDENTIFIER"}), 400

    success, msg, expires_in_or_wait = OTPService.resend_challenge(
        identifier=identifier,
        purpose=purpose
    )

    if success:
        return jsonify({
            "success": True,
            "message": "New OTP sent",
            "expires_in": expires_in_or_wait
        }), 200
    else:
        return jsonify({
            "success": False,
            "message": msg,
            "error_code": "COOLDOWN_ACTIVE",
            "wait_seconds": expires_in_or_wait
        }), 429


@api_bp.route("/dev/simulated-sms", methods=["GET"])
def api_get_simulated_sms():
    """Virtual phone simulator endpoint active ONLY in mock/demo development mode."""
    if current_app.config.get("OTP_PROVIDER_MODE") == "production" and not current_app.config.get("DEMO_MODE"):
        return jsonify({"success": False, "message": "Disabled in production."}), 403

    identifier = request.args.get("identifier", "").strip()
    latest = get_latest_mock_sms(identifier)
    if not latest and session.get("demo_otp"):
        code = session.get("demo_otp")
        latest = {
            "sender": "VM-JAGANP",
            "recipient": identifier,
            "raw_otp": code,
            "message": f"Your JaganPay verification code is {code}. Valid for 5 minutes.",
            "time": "Just now",
        }

    if not latest:
        return jsonify({"success": False, "message": "No simulated SMS received yet."}), 404

    return jsonify({
        "success": True,
        "sms": latest
    }), 200


@api_bp.route("/auth/login", methods=["POST"])
@limiter.limit("30 per hour")
def api_login():
    data = request.get_json() or {}
    identifier = data.get("identifier", "").strip().lower()
    password = data.get("password", "")

    user = User.query.filter(
        (User.email == identifier) | (User.phone == identifier)
    ).first()

    if not user or not user.check_password(password):
        return jsonify({"success": False, "message": "Invalid credentials.", "error_code": "AUTH_FAILED"}), 401

    if not user.is_active:
        return jsonify({"success": False, "message": "Account suspended.", "error_code": "ACCOUNT_SUSPENDED"}), 403

    if not user.is_verified:
        request_otp(user, purpose=OTPPurpose.REGISTRATION)
        return jsonify({
            "success": False,
            "message": "Account unverified. OTP sent.",
            "error_code": "UNVERIFIED",
            "data": {"user_id": user.id}
        }), 403

    login_user(user)
    return jsonify({
        "success": True,
        "message": "Login successful.",
        "data": user.to_dict()
    }), 200


@api_bp.route("/auth/logout", methods=["POST"])
def api_logout():
    if current_user.is_authenticated:
        logout_user()
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully."}), 200


# ----------------------------------------------------
# USER & ACCOUNTS APIS
# ----------------------------------------------------

@api_bp.route("/user/profile", methods=["GET", "PUT"])
def api_profile():
    if not current_user.is_authenticated:
        return jsonify({"success": False, "message": "Unauthorized", "error_code": "UNAUTHORIZED"}), 401

    if request.method == "PUT":
        data = request.get_json() or {}
        if "full_name" in data and len(data["full_name"]) >= 2:
            current_user.full_name = data["full_name"].strip()
            db.session.commit()

    return jsonify({"success": True, "data": current_user.to_dict()}), 200


@api_bp.route("/accounts", methods=["GET", "POST"])
def api_accounts():
    if not current_user.is_authenticated:
        return jsonify({"success": False, "message": "Unauthorized", "error_code": "UNAUTHORIZED"}), 401

    if request.method == "POST":
        data = request.get_json() or {}
        bank_name = data.get("bank_name", BankNames.JAGAN_BANK)
        import random
        masked = f"•••• •••• {random.randint(1000, 9999)}"
        acc = DemoBankAccount(
            user_id=current_user.id,
            bank_name=bank_name,
            account_holder=current_user.full_name,
            account_number_masked=masked,
            demo_balance=25000.0,
            is_primary=False,
        )
        db.session.add(acc)
        db.session.commit()
        return jsonify({"success": True, "message": "Demo account linked.", "data": acc.to_dict()}), 201

    accounts = [acc.to_dict() for acc in current_user.bank_accounts.all()]
    return jsonify({"success": True, "data": accounts}), 200


# ----------------------------------------------------
# PAYMENTS APIS
# ----------------------------------------------------

@api_bp.route("/payments/send", methods=["POST"])
def api_send_payment():
    if not current_user.is_authenticated:
        return jsonify({"success": False, "message": "Unauthorized", "error_code": "UNAUTHORIZED"}), 401

    data = request.get_json() or {}
    receiver_upi = data.get("receiver_upi", "").strip()
    try:
        amount = float(data.get("amount", 0))
    except (ValueError, TypeError):
        amount = 0.0

    pin = data.get("demo_pin", "")
    desc = data.get("description", "API Payment")
    category = data.get("category", SpendingCategory.OTHER)

    if not current_user.check_pin(pin):
        return jsonify({"success": False, "message": "Invalid demo PIN.", "error_code": "INVALID_PIN"}), 400

    success, message, txn = execute_simulated_transfer(
        sender=current_user,
        receiver_upi=receiver_upi,
        amount=amount,
        description=desc,
        category=category,
        txn_type=TransactionType.SEND,
    )

    if success and txn:
        return jsonify({"success": True, "message": message, "data": txn.to_dict()}), 200
    else:
        return jsonify({"success": False, "message": message, "error_code": "TRANSFER_FAILED"}), 400


@api_bp.route("/payments/receive", methods=["GET"])
def api_receive_payment():
    if not current_user.is_authenticated:
        return jsonify({"success": False, "message": "Unauthorized", "error_code": "UNAUTHORIZED"}), 401

    amount = request.args.get("amount", type=float)
    note = request.args.get("note", "Demo Payment")
    upi_str = build_upi_string(current_user.primary_upi, current_user.full_name, amount, note)
    qr_base64 = generate_qr_base64(upi_str)

    return jsonify({
        "success": True,
        "data": {
            "upi_id": current_user.primary_upi,
            "upi_uri": upi_str,
            "qr_code_base64": qr_base64,
        }
    }), 200


@api_bp.route("/payments/request", methods=["POST"])
def api_request_payment():
    if not current_user.is_authenticated:
        return jsonify({"success": False, "message": "Unauthorized", "error_code": "UNAUTHORIZED"}), 401

    data = request.get_json() or {}
    payer_upi = data.get("payer_upi", "").strip()
    amount = float(data.get("amount", 0))
    desc = data.get("description", "Demo Request")

    req = PaymentRequest(
        requester_id=current_user.id,
        payer_upi=payer_upi,
        amount=amount,
        description=desc,
        status="PENDING",
        expires_at=datetime.utcnow() + timedelta(days=3),
    )
    db.session.add(req)
    db.session.commit()

    return jsonify({"success": True, "message": "Payment request sent.", "data": req.to_dict()}), 201


@api_bp.route("/payments/qr", methods=["POST"])
def api_parse_qr():
    data = request.get_json() or {}
    payload = data.get("payload", "").strip()
    import urllib.parse
    if payload.startswith("upi://pay"):
        parsed = urllib.parse.urlparse(payload)
        qs = urllib.parse.parse_qs(parsed.query)
        return jsonify({
            "success": True,
            "data": {
                "upi_id": qs.get("pa", [""])[0],
                "name": qs.get("pn", [""])[0],
                "amount": float(qs.get("am", [0])[0]) if qs.get("am") else None,
                "note": qs.get("tn", [""])[0],
            }
        }), 200
    return jsonify({"success": False, "message": "Invalid UPI payload", "error_code": "INVALID_QR"}), 400


# ----------------------------------------------------
# TRANSACTIONS APIS
# ----------------------------------------------------

@api_bp.route("/transactions", methods=["GET"])
def api_transactions():
    if not current_user.is_authenticated:
        return jsonify({"success": False, "message": "Unauthorized", "error_code": "UNAUTHORIZED"}), 401

    txns = Transaction.query.filter(
        (Transaction.sender_id == current_user.id) | (Transaction.receiver_id == current_user.id)
    ).order_by(Transaction.created_at.desc()).limit(50).all()

    return jsonify({"success": True, "data": [t.to_dict() for t in txns]}), 200


@api_bp.route("/transactions/<txn_id>", methods=["GET"])
def api_transaction_detail(txn_id):
    if not current_user.is_authenticated:
        return jsonify({"success": False, "message": "Unauthorized", "error_code": "UNAUTHORIZED"}), 401

    txn = Transaction.query.get_or_404(txn_id)
    if txn.sender_id != current_user.id and txn.receiver_id != current_user.id and not current_user.is_admin:
        return jsonify({"success": False, "message": "Forbidden", "error_code": "FORBIDDEN"}), 403

    return jsonify({"success": True, "data": txn.to_dict()}), 200


# ----------------------------------------------------
# NOTIFICATIONS APIS
# ----------------------------------------------------

@api_bp.route("/notifications", methods=["GET"])
def api_notifications():
    if not current_user.is_authenticated:
        return jsonify({"success": False, "message": "Unauthorized", "error_code": "UNAUTHORIZED"}), 401

    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(30).all()
    return jsonify({"success": True, "data": [n.to_dict() for n in notifs]}), 200


@api_bp.route("/notifications/<int:notif_id>/read", methods=["PUT"])
def api_mark_notification_read(notif_id):
    if not current_user.is_authenticated:
        return jsonify({"success": False, "message": "Unauthorized", "error_code": "UNAUTHORIZED"}), 401

    notif = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first_or_404()
    notif.is_read = True
    db.session.commit()
    return jsonify({"success": True, "message": "Marked as read."}), 200


# ----------------------------------------------------
# ANALYTICS & RISK APIS
# ----------------------------------------------------

@api_bp.route("/analytics", methods=["GET"])
def api_analytics():
    if not current_user.is_authenticated:
        return jsonify({"success": False, "message": "Unauthorized", "error_code": "UNAUTHORIZED"}), 401

    debits = Transaction.query.filter_by(sender_id=current_user.id, status=TransactionStatus.SUCCESS).all()
    credits = Transaction.query.filter_by(receiver_id=current_user.id, status=TransactionStatus.SUCCESS).all()

    spent = sum(t.amount for t in debits)
    received = sum(t.amount for t in credits)

    return jsonify({
        "success": True,
        "data": {
            "total_spent": spent,
            "total_received": received,
            "net_flow": received - spent,
            "transaction_count": len(debits),
        }
    }), 200


@api_bp.route("/risk", methods=["GET"])
def api_risk():
    if not current_user.is_authenticated:
        return jsonify({"success": False, "message": "Unauthorized", "error_code": "UNAUTHORIZED"}), 401

    score, level, factors = calculate_simulated_risk(current_user.id, "check@jaganpay", 5000.0)
    return jsonify({
        "success": True,
        "data": {
            "simulated_score": score,
            "simulated_level": level,
            "factors": factors,
            "disclaimer": "Demo risk score generated from simulated transaction behavior.",
        }
    }), 200


# ----------------------------------------------------
# AI APIS
# ----------------------------------------------------

@api_bp.route("/ai/chat", methods=["POST"])
def api_ai_chat():
    data = request.get_json() or {}
    msg = data.get("message", "").strip()
    if not msg:
        return jsonify({"success": False, "message": "Message required", "error_code": "EMPTY_MESSAGE"}), 400

    ctx = {"name": current_user.full_name, "balance": current_user.total_demo_balance} if current_user.is_authenticated else {}
    reply = ai_service.ask_ai(msg, ctx)
    return jsonify({"success": True, "reply": reply}), 200


@api_bp.route("/ai/insights", methods=["POST"])
def api_ai_insights():
    if not current_user.is_authenticated:
        return jsonify({"success": False, "message": "Unauthorized", "error_code": "UNAUTHORIZED"}), 401

    debits = Transaction.query.filter_by(sender_id=current_user.id, status=TransactionStatus.SUCCESS).all()
    spent = sum(t.amount for t in debits)
    credits = Transaction.query.filter_by(receiver_id=current_user.id, status=TransactionStatus.SUCCESS).all()
    received = sum(t.amount for t in credits)

    metrics = {
        "total_spent": spent,
        "total_received": received,
        "net_flow": received - spent,
        "top_category": "General",
        "txn_count": len(debits),
    }
    insight = ai_service.generate_spending_insights(metrics)
    return jsonify({"success": True, "data": {"insight": insight}}), 200


# ----------------------------------------------------
# SUPPORT TICKETS APIS
# ----------------------------------------------------

@api_bp.route("/support/tickets", methods=["GET", "POST"])
def api_support_tickets():
    if not current_user.is_authenticated:
        return jsonify({"success": False, "message": "Unauthorized", "error_code": "UNAUTHORIZED"}), 401

    if request.method == "POST":
        data = request.get_json() or {}
        subject = data.get("subject", "").strip()
        description = data.get("description", "").strip()
        category = data.get("category", "GENERAL")
        priority = data.get("priority", "MEDIUM")

        if not subject or not description:
            return jsonify({"success": False, "message": "subject and description required", "error_code": "MISSING_FIELDS"}), 400

        ticket = SupportTicket(
            ticket_no=SupportTicket.generate_ticket_no(),
            user_id=current_user.id,
            subject=subject,
            category=category,
            priority=priority,
            description=description,
        )
        db.session.add(ticket)
        db.session.commit()
        return jsonify({"success": True, "message": "Ticket created.", "data": ticket.to_dict()}), 201

    tickets = [t.to_dict() for t in current_user.support_tickets.all()]
    return jsonify({"success": True, "data": tickets}), 200


# ----------------------------------------------------
# ADMIN REST APIS
# ----------------------------------------------------

@api_bp.route("/admin/users", methods=["GET"])
def api_admin_users():
    if not current_user.is_authenticated or not current_user.is_admin:
        return jsonify({"success": False, "message": "Admin privileges required", "error_code": "FORBIDDEN"}), 403

    users = [u.to_dict() for u in User.query.limit(100).all()]
    return jsonify({"success": True, "data": users}), 200


@api_bp.route("/admin/transactions", methods=["GET"])
def api_admin_transactions():
    if not current_user.is_authenticated or not current_user.is_admin:
        return jsonify({"success": False, "message": "Admin privileges required", "error_code": "FORBIDDEN"}), 403

    txns = [t.to_dict() for t in Transaction.query.order_by(Transaction.created_at.desc()).limit(100).all()]
    return jsonify({"success": True, "data": txns}), 200


@api_bp.route("/admin/risk-alerts", methods=["GET"])
def api_admin_risk_alerts():
    if not current_user.is_authenticated or not current_user.is_admin:
        return jsonify({"success": False, "message": "Admin privileges required", "error_code": "FORBIDDEN"}), 403

    alerts = [a.to_dict() for a in RiskAlert.query.order_by(RiskAlert.created_at.desc()).limit(100).all()]
    return jsonify({"success": True, "data": alerts}), 200


@api_bp.route("/admin/audit-logs", methods=["GET"])
def api_admin_audit_logs():
    if not current_user.is_authenticated or not current_user.is_admin:
        return jsonify({"success": False, "message": "Admin privileges required", "error_code": "FORBIDDEN"}), 403

    logs = [l.to_dict() for l in AuditLog.query.order_by(AuditLog.created_at.desc()).limit(100).all()]
    return jsonify({"success": True, "data": logs}), 200
