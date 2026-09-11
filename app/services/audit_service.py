import json
import logging
from flask import request
from app.extensions import db
from app.models.security import AuditLog, SecurityEvent

logger = logging.getLogger("jaganpay.audit")

SENSITIVE_KEYS = {"password", "confirm_password", "pin", "demo_pin", "otp", "code", "secret", "token", "cvv"}


def sanitize_dict(data: dict) -> dict:
    if not isinstance(data, dict):
        return {}
    sanitized = {}
    for k, v in data.items():
        if any(s in k.lower() for s in SENSITIVE_KEYS):
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, dict):
            sanitized[k] = sanitize_dict(v)
        else:
            sanitized[k] = v
    return sanitized


def log_audit(
    action: str,
    user_id: str = None,
    user_email: str = None,
    entity_type: str = None,
    entity_id: str = None,
    result: str = "SUCCESS",
    details: dict = None,
    ip_address: str = None,
):
    try:
        ip = ip_address or (request.remote_addr if request else "127.0.0.1")
        details_str = json.dumps(sanitize_dict(details)) if details else None

        audit = AuditLog(
            user_id=user_id,
            user_email=user_email,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            ip_address=ip,
            result=result,
            details=details_str,
        )
        db.session.add(audit)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Audit log recording error: {e}")


def log_security_event(
    event_type: str,
    user_id: str = None,
    status: str = "SUCCESS",
    details: dict = None,
):
    try:
        ip = request.remote_addr if request else "127.0.0.1"
        user_agent = request.user_agent.string[:250] if request and request.user_agent else "Unknown"
        details_str = json.dumps(sanitize_dict(details)) if details else None

        sec = SecurityEvent(
            user_id=user_id,
            event_type=event_type,
            ip_address=ip,
            user_agent=user_agent,
            status=status,
            details=details_str,
        )
        db.session.add(sec)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Security event recording error: {e}")
