from flask import Blueprint, render_template, jsonify, send_from_directory, current_app, make_response
from app.extensions import db

main_bp = Blueprint("main", __name__)


@main_bp.route("/manifest.json")
def manifest():
    return send_from_directory(current_app.static_folder, "manifest.json", mimetype="application/manifest+json")


@main_bp.route("/sw.js")
def service_worker():
    response = make_response(send_from_directory(current_app.static_folder, "sw.js", mimetype="application/javascript"))
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/about")
def about():
    return render_template("about.html")


@main_bp.route("/health")
def health():
    db_status = "healthy"
    try:
        db.session.execute(db.text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return jsonify({
        "status": "UP",
        "app": "JaganPay",
        "version": "2.0.0",
        "database": db_status,
        "mode": "DEMO_SIMULATION",
        "real_financial_transactions": False,
    })
