from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.middleware.auth_guard import verified_required
from app.models.ai_log import AIInteraction
from app.models.transaction import Transaction, TransactionStatus
from app.ai.gemini_service import ai_service

ai_bp = Blueprint("ai", __name__)


@ai_bp.route("/ai-assistant")
@login_required
@verified_required
def assistant():
    # Fetch recent AI interactions
    history = AIInteraction.query.filter_by(
        user_id=current_user.id
    ).order_by(AIInteraction.created_at.desc()).limit(10).all()

    return render_template("ai/assistant.html", history=reversed(history))


@ai_bp.route("/ai/chat", methods=["POST"])
@login_required
@verified_required
def chat():
    data = request.get_json() or {}
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"success": False, "message": "Message cannot be empty."}), 400

    # Collect live user context for AI enrichment
    debits = Transaction.query.filter_by(
        sender_id=current_user.id,
        status=TransactionStatus.SUCCESS
    ).all()
    spent = sum(t.amount for t in debits)

    context = {
        "name": current_user.full_name,
        "balance": current_user.total_demo_balance,
        "spent": spent,
        "upi_id": current_user.primary_upi,
    }

    ai_reply = ai_service.ask_ai(message, context)

    # Log interaction
    interaction = AIInteraction(
        user_id=current_user.id,
        prompt_summary=message[:250],
        response_snippet=ai_reply[:500],
        model_used="gemini-2.5-flash",
    )
    db.session.add(interaction)
    db.session.commit()

    return jsonify({
        "success": True,
        "reply": ai_reply,
        "is_simulated": True,
    })
