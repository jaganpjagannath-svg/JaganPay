from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.middleware.auth_guard import verified_required
from app.models.support import SupportTicket, SupportMessage, TicketStatus, TicketPriority
from app.services.webhook_service import dispatch_event
from app.services.audit_service import log_audit

support_bp = Blueprint("support", __name__)


@support_bp.route("/support", methods=["GET", "POST"])
@login_required
@verified_required
def index():
    if request.method == "POST":
        subject = request.form.get("subject", "").strip()
        category = request.form.get("category", "GENERAL")
        priority = request.form.get("priority", TicketPriority.MEDIUM)
        description = request.form.get("description", "").strip()

        if not subject or not description:
            flash("Please provide both a subject and a description for your request.", "danger")
            return redirect(url_for("support.index"))

        ticket = SupportTicket(
            ticket_no=SupportTicket.generate_ticket_no(),
            user_id=current_user.id,
            subject=subject,
            category=category,
            priority=priority,
            description=description,
            status=TicketStatus.OPEN,
        )
        db.session.add(ticket)
        db.session.commit()

        # Initial message
        first_msg = SupportMessage(
            ticket_id=ticket.id,
            sender_id=current_user.id,
            sender_name=current_user.full_name,
            message=description,
            is_admin_reply=False,
        )
        db.session.add(first_msg)
        db.session.commit()

        # Dispatch n8n webhook
        dispatch_event("SUPPORT", {
            "ticket_no": ticket.ticket_no,
            "user_email": current_user.email,
            "subject": ticket.subject,
            "priority": ticket.priority,
        })

        log_audit("TICKET_CREATED", current_user.id, current_user.email, "TICKET", ticket.ticket_no, "SUCCESS")
        flash(f"Support ticket {ticket.ticket_no} submitted successfully. An agent will review it.", "success")
        return redirect(url_for("support.detail", ticket_id=ticket.id))

    tickets = SupportTicket.query.filter_by(
        user_id=current_user.id
    ).order_by(SupportTicket.created_at.desc()).all()

    return render_template("support/index.html", tickets=tickets)


@support_bp.route("/support/<int:ticket_id>", methods=["GET", "POST"])
@login_required
@verified_required
def detail(ticket_id):
    ticket = SupportTicket.query.get_or_404(ticket_id)

    if ticket.user_id != current_user.id and not current_user.is_admin:
        flash("You are not authorized to view this ticket.", "danger")
        return redirect(url_for("support.index"))

    if request.method == "POST":
        reply_msg = request.form.get("message", "").strip()
        if reply_msg:
            msg = SupportMessage(
                ticket_id=ticket.id,
                sender_id=current_user.id,
                sender_name=current_user.full_name,
                message=reply_msg,
                is_admin_reply=current_user.is_admin,
            )
            db.session.add(msg)
            if current_user.is_admin:
                ticket.status = TicketStatus.IN_PROGRESS
            db.session.commit()
            flash("Message added to conversation.", "success")
            return redirect(url_for("support.detail", ticket_id=ticket.id))

    messages = ticket.messages.all()
    return render_template("support/detail.html", ticket=ticket, messages=messages)
