import os
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from config import config_by_name
from app.extensions import db, bcrypt, login_manager, csrf, limiter
from app.models.user import User
from app.models.notification import Notification
from app.middleware.security_headers import setup_security_headers
from app.utils.helpers import format_currency, mask_account_number, mask_email, mask_phone


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


def create_app(config_name="default"):
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static"
    )

    # Configure application
    conf = config_by_name.get(config_name or "default", config_by_name["default"])
    app.config.from_object(conf)

    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # Apply security headers
    setup_security_headers(app)

    # Context processors for Jinja templates
    @app.context_processor
    def inject_globals():
        unread_count = 0
        from flask_login import current_user
        if current_user.is_authenticated:
            try:
                unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
            except Exception:
                unread_count = 0

        return {
            "format_currency": format_currency,
            "mask_account_number": mask_account_number,
            "mask_email": mask_email,
            "mask_phone": mask_phone,
            "unread_count": unread_count,
            "current_year": datetime.utcnow().year,
            "demo_mode": app.config.get("DEMO_MODE", True),
        }

    # Register Blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.payments import payments_bp
    from app.routes.transactions import transactions_bp
    from app.routes.analytics import analytics_bp
    from app.routes.ai import ai_bp
    from app.routes.security import security_bp
    from app.routes.support import support_bp
    from app.routes.merchant import merchant_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(security_bp)
    app.register_blueprint(support_bp)
    app.register_blueprint(merchant_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    # Exempt REST API from CSRF protection for seamless client/mobile/automated testing
    csrf.exempt(api_bp)

    # Global Error Handlers
    @app.errorhandler(400)
    def bad_request(e):
        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"success": False, "message": "Bad Request", "error_code": "BAD_REQUEST"}), 400
        return render_template("errors/400.html", error=e), 400

    @app.errorhandler(401)
    def unauthorized(e):
        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"success": False, "message": "Authentication required", "error_code": "UNAUTHORIZED"}), 401
        return render_template("errors/401.html", error=e), 401

    @app.errorhandler(403)
    def forbidden(e):
        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"success": False, "message": "Permission denied", "error_code": "FORBIDDEN"}), 403
        return render_template("errors/403.html", error=e), 403

    @app.errorhandler(404)
    def not_found(e):
        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"success": False, "message": "Resource not found", "error_code": "NOT_FOUND"}), 404
        return render_template("errors/404.html", error=e), 404

    @app.errorhandler(429)
    def ratelimit_exceeded(e):
        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"success": False, "message": "Rate limit exceeded. Please slow down.", "error_code": "RATE_LIMIT"}), 429
        return render_template("errors/429.html", error=e), 429

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"success": False, "message": "Internal Server Error", "error_code": "INTERNAL_SERVER_ERROR"}), 500
        return render_template("errors/500.html", error=e), 500

    # Auto create tables for local development
    with app.app_context():
        db.create_all()

    return app


# Lazy WSGI application fallback if WSGI servers invoke `gunicorn app:app`
_default_app = None

def __getattr__(name):
    if name == "app":
        global _default_app
        if _default_app is None:
            _default_app = create_app(os.environ.get("FLASK_ENV", "production"))
        return _default_app
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

