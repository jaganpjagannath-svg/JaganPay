from functools import wraps
from flask import flash, redirect, url_for, request, jsonify, abort
from flask_login import current_user


def verified_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"success": False, "message": "Authentication required", "error_code": "UNAUTHORIZED"}), 401
            return redirect(url_for("auth.login", next=request.url))
        if not current_user.is_verified:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"success": False, "message": "Account verification required", "error_code": "UNVERIFIED"}), 403
            flash("Please verify your account using the OTP sent to your registered contact.", "warning")
            return redirect(url_for("auth.verify_otp"))
        if not current_user.is_active:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"success": False, "message": "Account suspended", "error_code": "SUSPENDED"}), 403
            flash("Your account has been suspended. Please contact JaganPay support.", "danger")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"success": False, "message": "Authentication required", "error_code": "UNAUTHORIZED"}), 401
            return redirect(url_for("auth.login", next=request.url))
        if not current_user.is_admin:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"success": False, "message": "Admin privileges required", "error_code": "FORBIDDEN"}), 403
            flash("Access denied. Admin privileges are required to view this page.", "danger")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    return decorated_function


def merchant_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"success": False, "message": "Authentication required", "error_code": "UNAUTHORIZED"}), 401
            return redirect(url_for("auth.login", next=request.url))
        if not current_user.is_merchant and not current_user.is_admin:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"success": False, "message": "Merchant account required", "error_code": "FORBIDDEN"}), 403
            flash("Merchant access required. You can register as a merchant in your profile.", "info")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    return decorated_function
