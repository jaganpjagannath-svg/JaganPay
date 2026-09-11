import re


def validate_email(email: str) -> bool:
    if not email or len(email) > 120:
        return False
    regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return bool(re.match(regex, email))


def validate_phone(phone: str) -> bool:
    if not phone:
        return False
    # Accepts 10 to 15 digits, optionally prefixed with +
    clean = re.sub(r"[\s\-\(\)]", "", phone)
    return bool(re.match(r"^\+?[0-9]{10,15}$", clean))


def validate_upi_id(upi_id: str) -> bool:
    if not upi_id:
        return False
    # Format: handle@provider (e.g. jagan@jaganpay)
    regex = r"^[a-zA-Z0-9.\-_]{2,50}@[a-zA-Z0-9.\-_]{2,30}$"
    return bool(re.match(regex, upi_id.strip()))


def validate_pin(pin: str) -> bool:
    if not pin:
        return False
    # 4 to 6 digit numeric PIN
    return bool(re.match(r"^\d{4,6}$", pin.strip()))


def validate_password_strength(password: str) -> tuple[bool, str]:
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one digit."
    return True, "Password is valid."
