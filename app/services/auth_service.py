import logging
from flask import current_app
from app.extensions import db
from app.models.user import User
from app.models.otp import OTPPurpose, OTPChannel, OTPChallenge
from app.services.otp_service import OTPService

logger = logging.getLogger("jaganpay.auth")


def request_otp(
    user: User,
    purpose: str = OTPPurpose.REGISTRATION,
    channel: str = OTPChannel.SMS
) -> tuple[bool, str, None]:
    """
    Generate, hash, store OTP challenge and dispatch via OTP provider (Mock SMS/Email in dev, Real in prod).
    Returns (success, message, None). The plaintext OTP is NEVER returned to callers.
    """
    try:
        identifier = user.phone if channel == OTPChannel.SMS and user.phone else user.email
        challenge, expires_in = OTPService.create_challenge(
            identifier=identifier,
            channel=channel,
            purpose=purpose,
            user_id=user.id
        )
        channel_name = "mobile number via SMS" if channel == OTPChannel.SMS else "email address"
        return True, f"Verification code dispatched to your registered {channel_name}.", None

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error requesting OTP for user {user.id}: {e}")
        return False, "Failed to generate verification code. Please try again.", None


def verify_user_otp(user: User, raw_code: str, purpose: str = None) -> tuple[bool, str]:
    """
    Verify an OTP code against active challenges using timing-safe comparison.
    Checks challenges tied to user's phone, email, or user_id.
    """
    # First attempt verification using user_id
    success, msg, challenge = OTPService.verify_challenge(
        raw_code=raw_code,
        identifier=user.phone or user.email,
        purpose=purpose,
        user_id=user.id
    )

    if not success and user.email and user.email != user.phone:
        # Fallback to checking email identifier if different
        alt_success, alt_msg, alt_challenge = OTPService.verify_challenge(
            raw_code=raw_code,
            identifier=user.email,
            purpose=purpose,
            user_id=user.id
        )
        if alt_success:
            return True, alt_msg

    return success, msg
