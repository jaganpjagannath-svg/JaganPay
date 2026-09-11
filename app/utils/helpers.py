import re
import random
from datetime import datetime


def format_currency(amount: float) -> str:
    """Format a number into Indian Rupee format (e.g. ₹25,000.00)."""
    try:
        val = float(amount)
        # Indian numbering system formatting
        s = f"{val:,.2f}"
        return f"₹{s}"
    except (ValueError, TypeError):
        return f"₹0.00"


def mask_account_number(account_no: str) -> str:
    """Mask account number showing only last 4 digits."""
    clean = re.sub(r"\D", "", str(account_no))
    if len(clean) <= 4:
        return f"•••• {clean}"
    last_four = clean[-4:]
    return f"•••• •••• {last_four}"


def mask_email(email: str) -> str:
    """Mask email e.g. j***n@jaganpay.com"""
    if not email or "@" not in email:
        return email or ""
    parts = email.split("@")
    user, domain = parts[0], parts[1]
    if len(user) <= 2:
        masked_user = user[0] + "*"
    else:
        masked_user = user[0] + ("*" * (len(user) - 2)) + user[-1]
    return f"{masked_user}@{domain}"


def mask_phone(phone: str) -> str:
    """Mask phone e.g. +91 ••••• ••421"""
    clean = re.sub(r"\D", "", str(phone))
    if len(clean) <= 4:
        return phone
    last_four = clean[-4:]
    return f"••••••{last_four}"


def generate_reference_no(prefix: str = "JGP") -> str:
    """Generate realistic simulated transaction reference: e.g. JGP2026091189421"""
    now = datetime.utcnow()
    date_str = now.strftime("%Y%m%d")
    random_digits = f"{random.randint(10000, 99999)}"
    return f"{prefix}{date_str}{random_digits}"
