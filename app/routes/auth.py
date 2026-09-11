import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db, limiter
from app.models.user import User, Role
from app.models.otp import OTPPurpose, OTPChannel
from app.models.bank_account import DemoBankAccount, UPIProfile, BankNames
from app.services.auth_service import request_otp, verify_user_otp
from app.services.audit_service import log_audit, log_security_event
from app.services.webhook_service import dispatch_event
from app.utils.validators import validate_email, validate_phone, validate_password_strength

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def register():
    if current_user.is_authenticated and current_user.is_verified:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validations
        if not full_name or len(full_name) < 2:
            flash("Please provide your full legal or display name.", "danger")
            return render_template("auth/register.html")

        if not validate_email(email):
            flash("Please enter a valid email address.", "danger")
            return render_template("auth/register.html")

        if not validate_phone(phone):
            flash("Please enter a valid 10-digit phone number.", "danger")
            return render_template("auth/register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html")

        is_valid_pw, pw_msg = validate_password_strength(password)
        if not is_valid_pw:
            flash(pw_msg, "danger")
            return render_template("auth/register.html")

        # Check existing user
        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists. Please login.", "warning")
            return redirect(url_for("auth.login"))

        if User.query.filter_by(phone=phone).first():
            flash("This phone number is already registered.", "warning")
            return render_template("auth/register.html")

        # Create user (unverified)
        user = User(
            full_name=full_name,
            email=email,
            phone=phone,
            role=Role.USER,
            is_verified=False,
            is_active=True,
        )
        user.set_password(password)
        # Default demo PIN: 1234
        user.set_pin("1234")
        db.session.add(user)
        db.session.commit()

        # Generate unique UPI ID
        handle = re.sub(r"[^a-zA-Z0-9]", "", email.split("@")[0]).lower()
        base_upi = f"{handle}@jaganpay"
        upi_candidate = base_upi
        counter = 1
        while UPIProfile.query.filter_by(upi_id=upi_candidate).first():
            upi_candidate = f"{handle}{counter}@jaganpay"
            counter += 1

        upi_profile = UPIProfile(
            user_id=user.id,
            upi_id=upi_candidate,
            qr_data=f"upi://pay?pa={upi_candidate}&pn={user.full_name}&cu=INR&mode=02",
            is_active=True,
        )
        db.session.add(upi_profile)

        # Seed initial Demo Bank Account with ₹25,000 demo balance
        demo_acc = DemoBankAccount(
            user_id=user.id,
            bank_name=BankNames.JAGAN_BANK,
            account_holder=user.full_name,
            account_number_masked=f"•••• •••• {user.phone[-4:] if len(user.phone) >= 4 else '1001'}",
            ifsc_code="JAGB0001001",
            account_type="SAVINGS",
            demo_balance=25000.0,
            is_primary=True,
        )
        db.session.add(demo_acc)
        db.session.commit()

        # Request initial mandatory OTP via SMS provider
        request_otp(user, purpose=OTPPurpose.REGISTRATION, channel=OTPChannel.SMS)

        # Dispatch registration webhook to n8n
        dispatch_event("REGISTRATION", {
            "user_id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "upi_id": upi_candidate,
        })

        log_audit("USER_REGISTERED", user.id, user.email, "USER", user.id, "SUCCESS")

        session["pending_verification_user_id"] = user.id
        flash(f"Registration initiated! A 6-digit verification code has been dispatched to your mobile number.", "success")
        return redirect(url_for("auth.verify_otp"))

    return render_template("auth/register.html")


@auth_bp.route("/verify-otp", methods=["GET", "POST"])
@limiter.limit("20 per hour")
def verify_otp():
    user_id = session.get("pending_verification_user_id")
    if not user_id and current_user.is_authenticated:
        user_id = current_user.id

    if not user_id:
        flash("No active verification session found. Please login or register.", "warning")
        return redirect(url_for("auth.login"))

    user = User.query.get(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("auth.register"))

    if request.method == "POST":
        raw_code = request.form.get("otp", "").strip()
        # Fallback to concatenate individual digit inputs if submitted separately
        if not raw_code:
            raw_code = "".join([request.form.get(f"digit_{i}", "").strip() for i in range(1, 7)])

        if not raw_code or len(raw_code) != 6:
            flash("Please enter a valid 6-digit OTP code.", "danger")
            return render_template("auth/verify_otp.html", user=user)

        success, msg = verify_user_otp(user, raw_code)
        if success:
            session.pop("pending_verification_user_id", None)
            login_user(user)
            flash("Account verified successfully! Welcome to JaganPay.", "success")
            return redirect(url_for("dashboard.index"))
        else:
            flash(msg, "danger")

    return render_template("auth/verify_otp.html", user=user)


@auth_bp.route("/resend-otp", methods=["POST"])
@limiter.limit("10 per 15 minutes")
def resend_otp():
    user_id = session.get("pending_verification_user_id")
    if not user_id and current_user.is_authenticated:
        user_id = current_user.id

    if not user_id:
        flash("Session expired. Please sign in again.", "warning")
        return redirect(url_for("auth.login"))

    user = User.query.get(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("auth.login"))

    success, msg, _ = request_otp(user, purpose=OTPPurpose.REGISTRATION, channel=OTPChannel.SMS)
    if success:
        flash("A fresh verification code has been dispatched to your mobile number.", "success")
    else:
        flash(msg, "warning")

    return redirect(url_for("auth.verify_otp"))


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("15 per 15 minutes")
def login():
    if current_user.is_authenticated and current_user.is_verified:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter(
            (User.email == identifier) | (User.phone == identifier)
        ).first()

        if not user or not user.check_password(password):
            log_security_event("LOGIN_FAILED", getattr(user, "id", None), "FAILURE", {"identifier": identifier})
            flash("Invalid email/phone or password.", "danger")
            return render_template("auth/login.html")

        if not user.is_active:
            flash("Your account has been deactivated or suspended. Please contact support.", "danger")
            return render_template("auth/login.html")

        if not user.is_verified:
            session["pending_verification_user_id"] = user.id
            request_otp(user, purpose=OTPPurpose.REGISTRATION)
            flash("Please verify your account OTP to proceed.", "info")
            return redirect(url_for("auth.verify_otp"))

        # Successful login
        login_user(user)
        log_security_event("LOGIN_SUCCESS", user.id, "SUCCESS")
        log_audit("USER_LOGIN", user.id, user.email, "USER", user.id, "SUCCESS")

        flash(f"Welcome back, {user.full_name}!", "success")
        next_page = request.args.get("next")
        if next_page and next_page.startswith("/"):
            return redirect(next_page)
        return redirect(url_for("dashboard.index"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    uid = current_user.id
    email = current_user.email
    logout_user()
    session.clear()
    log_security_event("SESSION_LOGOUT", uid, "SUCCESS")
    log_audit("USER_LOGOUT", uid, email, "USER", uid, "SUCCESS")
    flash("You have been logged out securely.", "info")
    return redirect(url_for("auth.login"))
