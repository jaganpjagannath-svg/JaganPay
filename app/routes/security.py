from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from app.extensions import db
from app.middleware.auth_guard import verified_required
from app.models.security import SecurityEvent
from app.models.bank_account import DemoBankAccount, BankNames
from app.models.otp import OTPPurpose
from app.services.auth_service import request_otp, verify_user_otp
from app.services.audit_service import log_audit, log_security_event
from app.utils.validators import validate_pin, validate_password_strength

security_bp = Blueprint("security", __name__)


@security_bp.route("/security")
@login_required
@verified_required
def index():
    events = current_user.security_events.limit(10).all()
    accounts = current_user.bank_accounts.all()

    return render_template(
        "security/index.html",
        user=current_user,
        events=events,
        accounts=accounts,
        bank_names=BankNames.ALL,
    )


@security_bp.route("/security/change-pin", methods=["POST"])
@login_required
@verified_required
def change_pin():
    new_pin = request.form.get("new_pin", "").strip()
    otp_code = request.form.get("otp_code", "").strip()

    if not validate_pin(new_pin):
        flash("Demo PIN must be 4 to 6 numeric digits.", "danger")
        return redirect(url_for("security.index"))

    # Verify sensitive action OTP
    if not otp_code:
        request_otp(current_user, purpose=OTPPurpose.PIN_CHANGE)
        flash("Changing your Demo PIN requires OTP verification. A security code was dispatched.", "info")
        return redirect(url_for("security.index", pin_otp_required=True))

    valid, msg = verify_user_otp(current_user, otp_code, purpose=OTPPurpose.PIN_CHANGE)
    if not valid:
        flash(f"PIN change failed: {msg}", "danger")
        return redirect(url_for("security.index"))

    current_user.set_pin(new_pin)
    db.session.commit()

    log_security_event("PIN_CHANGED", current_user.id, "SUCCESS")
    log_audit("PIN_CHANGED", current_user.id, current_user.email, "USER", current_user.id, "SUCCESS")

    flash("Your Demo PIN has been updated successfully!", "success")
    return redirect(url_for("security.index"))


@security_bp.route("/security/change-password", methods=["POST"])
@login_required
@verified_required
def change_password():
    current_pw = request.form.get("current_password", "")
    new_pw = request.form.get("new_password", "")
    confirm_pw = request.form.get("confirm_password", "")

    if not current_user.check_password(current_pw):
        flash("Current password is incorrect.", "danger")
        return redirect(url_for("security.index"))

    if new_pw != confirm_pw:
        flash("New passwords do not match.", "danger")
        return redirect(url_for("security.index"))

    is_valid, msg = validate_password_strength(new_pw)
    if not is_valid:
        flash(msg, "danger")
        return redirect(url_for("security.index"))

    current_user.set_password(new_pw)
    db.session.commit()

    log_security_event("PASSWORD_CHANGED", current_user.id, "SUCCESS")
    log_audit("PASSWORD_CHANGED", current_user.id, current_user.email, "USER", current_user.id, "SUCCESS")

    flash("Password updated successfully.", "success")
    return redirect(url_for("security.index"))


@security_bp.route("/security/add-account", methods=["POST"])
@login_required
@verified_required
def add_account():
    bank_name = request.form.get("bank_name", BankNames.JAGAN_BANK)
    account_type = request.form.get("account_type", "SAVINGS")

    # Generate realistic simulated masked number
    import random
    raw_acc = str(random.randint(1000000000, 9999999999))
    masked = f"•••• •••• {raw_acc[-4:]}"

    ifsc_prefix = "JAGB" if "Jagan" in bank_name else ("ASTR" if "Astra" in bank_name else "DNBL")
    ifsc = f"{ifsc_prefix}000{random.randint(1000, 9999)}"

    new_acc = DemoBankAccount(
        user_id=current_user.id,
        bank_name=bank_name,
        account_holder=current_user.full_name,
        account_number_masked=masked,
        ifsc_code=ifsc,
        account_type=account_type,
        demo_balance=25000.0,
        is_primary=False,
    )
    db.session.add(new_acc)
    db.session.commit()

    log_audit("BANK_ACCOUNT_ADDED", current_user.id, current_user.email, "ACCOUNT", str(new_acc.id), "SUCCESS")
    flash(f"Simulated account at {bank_name} added with ₹25,000 demo balance!", "success")
    return redirect(url_for("security.index"))
