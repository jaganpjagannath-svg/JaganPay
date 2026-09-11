from flask import Blueprint, render_template, request, abort, make_response
from flask_login import login_required, current_user
from app.middleware.auth_guard import verified_required
from app.models.transaction import Transaction, TransactionStatus, TransactionType

transactions_bp = Blueprint("transactions", __name__)


@transactions_bp.route("/transactions")
@login_required
@verified_required
def history():
    page = request.args.get("page", 1, type=int)
    filter_type = request.args.get("filter", "all").lower()
    search_q = request.args.get("q", "").strip()

    query = Transaction.query.filter(
        (Transaction.sender_id == current_user.id) | (Transaction.receiver_id == current_user.id)
    )

    if filter_type == "sent":
        query = query.filter(Transaction.sender_id == current_user.id)
    elif filter_type == "received":
        query = query.filter(Transaction.receiver_id == current_user.id)
    elif filter_type == "success":
        query = query.filter(Transaction.status == TransactionStatus.SUCCESS)
    elif filter_type == "failed":
        query = query.filter(Transaction.status == TransactionStatus.FAILED)
    elif filter_type == "merchant":
        query = query.filter(Transaction.type == TransactionType.MERCHANT_PAYMENT)
    elif filter_type == "qr":
        query = query.filter(Transaction.type == TransactionType.QR_PAYMENT)

    if search_q:
        query = query.filter(
            (Transaction.reference_no.ilike(f"%{search_q}%")) |
            (Transaction.sender_upi.ilike(f"%{search_q}%")) |
            (Transaction.receiver_upi.ilike(f"%{search_q}%")) |
            (Transaction.description.ilike(f"%{search_q}%"))
        )

    pagination = query.order_by(Transaction.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )

    return render_template(
        "transactions/history.html",
        transactions=pagination.items,
        pagination=pagination,
        current_filter=filter_type,
        search_q=search_q
    )


@transactions_bp.route("/transactions/<txn_id>")
@login_required
@verified_required
def detail(txn_id):
    txn = Transaction.query.get_or_404(txn_id)

    # Permission check: current user must be sender, receiver, or admin
    if txn.sender_id != current_user.id and txn.receiver_id != current_user.id and not current_user.is_admin:
        abort(403)

    return render_template("transactions/detail.html", txn=txn)


@transactions_bp.route("/receipt/<txn_id>")
@login_required
@verified_required
def receipt(txn_id):
    txn = Transaction.query.get_or_404(txn_id)

    if txn.sender_id != current_user.id and txn.receiver_id != current_user.id and not current_user.is_admin:
        abort(403)

    return render_template("payments/receipt.html", txn=txn)
