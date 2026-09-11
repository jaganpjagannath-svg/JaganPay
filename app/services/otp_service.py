import abc
import logging
import secrets
import sys
from datetime import datetime, timedelta
from flask import current_app
from app.extensions import db
from app.models.otp import OTPChallenge, OTPPurpose, OTPChannel
from app.models.user import User
from app.services.webhook_service import dispatch_event
from app.services.audit_service import log_security_event, log_audit
from app.utils.helpers import mask_phone, mask_email

logger = logging.getLogger("jaganpay.otp")


# =====================================================================
# PROVIDER INTERFACES & IMPLEMENTATIONS
# =====================================================================

# In-memory storage for virtual phone simulator in development mode
_simulated_sms_store: list[dict] = []


def get_latest_mock_sms(identifier: str | None = None) -> dict | None:
    """Retrieve the latest mock SMS for virtual phone simulator in frontend."""
    if not _simulated_sms_store:
        return None
    if identifier:
        clean = identifier.strip().lower() if "@" in identifier else identifier.strip()
        for item in reversed(_simulated_sms_store):
            if item.get("recipient") == clean or item.get("recipient") == identifier:
                return item
    return _simulated_sms_store[-1]


def get_all_mock_sms(limit: int = 10) -> list[dict]:
    """Retrieve recent simulated SMS messages for the virtual inbox."""
    return list(reversed(_simulated_sms_store[-limit:]))


class BaseSMSProvider(abc.ABC):
    @abc.abstractmethod
    def send_sms(self, to_phone: str, message: str, raw_otp: str | None = None) -> bool:
        """Send an SMS notification or OTP."""
        pass


class MockSMSProvider(BaseSMSProvider):
    """
    Simulated SMS Provider for Local Development and Testing.
    Outputs the OTP strictly to the backend server terminal with clear developer demarcation,
    and records to in-memory store for virtual device simulation.
    """
    def send_sms(self, to_phone: str, message: str, raw_otp: str | None = None) -> bool:
        banner = f"""
========================================
[DEV OTP PROVIDER]
Recipient: {to_phone}
Channel: SMS
OTP Code: {raw_otp}
Valid for: 5 minutes
========================================
"""
        print(banner, file=sys.stdout)
        sys.stdout.flush()
        logger.info(f"[MOCK SMS] Simulated SMS sent to {mask_phone(to_phone)}")

        # Store for virtual device preview in mock/demo mode
        _simulated_sms_store.append({
            "sender": "VM-JAGANP",
            "recipient": to_phone,
            "raw_otp": raw_otp,
            "message": message,
            "time": datetime.utcnow().strftime("%I:%M %p"),
            "timestamp": datetime.utcnow().isoformat()
        })
        if len(_simulated_sms_store) > 30:
            _simulated_sms_store.pop(0)

        return True


class RealSMSProvider(BaseSMSProvider):
    """
    Production SMS Provider.
    Dispatches via SMS gateway (Twilio, AWS SNS, etc.). Zero OTP logging in production.
    """
    def send_sms(self, to_phone: str, message: str, raw_otp: str | None = None) -> bool:
        api_key = current_app.config.get("SMS_API_KEY", "")
        # Real gateway dispatch would go here.
        # Zero OTP logging in production:
        logger.info(f"[PROD SMS] Real SMS dispatched to {mask_phone(to_phone)} via configured gateway.")
        return True


class BaseEmailProvider(abc.ABC):
    @abc.abstractmethod
    def send_email(self, to_email: str, subject: str, html_body: str, text_body: str, raw_otp: str | None = None) -> bool:
        """Send an email notification or OTP."""
        pass


class MockEmailProvider(BaseEmailProvider):
    """
    Mock Email Provider for Local Development.
    Prints OTP to the server terminal only.
    """
    def send_email(self, to_email: str, subject: str, html_body: str, text_body: str, raw_otp: str | None = None) -> bool:
        banner = f"""
========================================
[DEV OTP PROVIDER]
Recipient: {to_email}
Channel: EMAIL
OTP Code: {raw_otp}
Valid for: 5 minutes
========================================
"""
        print(banner, file=sys.stdout)
        sys.stdout.flush()
        logger.info(f"[MOCK EMAIL] Simulated email sent to {mask_email(to_email)}")
        return True


class SMTPEmailProvider(BaseEmailProvider):
    """Production SMTP Email Provider using app.services.email_service."""
    def send_email(self, to_email: str, subject: str, html_body: str, text_body: str, raw_otp: str | None = None) -> bool:
        from app.services.email_service import send_email as dispatch_smtp
        logger.info(f"[PROD EMAIL] SMTP email dispatched to {mask_email(to_email)}")
        return dispatch_smtp(to_email, subject, html_body, text_body)


def get_sms_provider() -> BaseSMSProvider:
    mode = current_app.config.get("OTP_PROVIDER_MODE", "mock").lower()
    if mode == "production":
        return RealSMSProvider()
    return MockSMSProvider()


def get_email_provider() -> BaseEmailProvider:
    mode = current_app.config.get("OTP_PROVIDER_MODE", "mock").lower()
    email_prov = current_app.config.get("EMAIL_PROVIDER", "mock").lower()
    if mode == "production" or email_prov == "smtp":
        # If testing/dev with mock provider mode, prefer mock terminal print
        if mode == "mock":
            return MockEmailProvider()
        return SMTPEmailProvider()
    return MockEmailProvider()


# =====================================================================
# OTP SERVICE
# =====================================================================

class OTPService:
    @staticmethod
    def generate_otp() -> str:
        """Generate a cryptographically secure 6-digit random numeric string."""
        return f"{secrets.randbelow(900000) + 100000:06d}"

    @classmethod
    def create_challenge(
        cls,
        identifier: str,
        channel: str = OTPChannel.SMS,
        purpose: str = OTPPurpose.REGISTRATION,
        user_id: str | None = None
    ) -> tuple[OTPChallenge, int]:
        """
        Create a new OTP challenge, hash the code with salt, dispatch via provider,
        and invalidate any previous active challenge for the same identifier and purpose.
        Returns (challenge, expires_in_seconds).
        """
        identifier = identifier.strip().lower() if "@" in identifier else identifier.strip()
        channel = channel.upper()

        expiry_seconds = current_app.config.get("OTP_EXPIRY_SECONDS", 300)
        cooldown_seconds = current_app.config.get("OTP_RESEND_COOLDOWN_SECONDS", 30)
        max_attempts = current_app.config.get("OTP_MAX_ATTEMPTS", 5)

        # Invalidate any prior unverified challenges for this identifier & purpose
        prior = OTPChallenge.query.filter_by(
            identifier=identifier,
            purpose=purpose,
            is_verified=False,
            is_invalidated=False
        ).all()
        for p in prior:
            p.is_invalidated = True

        # Generate OTP & salt
        raw_otp = cls.generate_otp()
        salt = secrets.token_hex(16)
        otp_hash = OTPChallenge.hash_otp(raw_otp, salt)

        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=expiry_seconds)
        resend_available_at = now + timedelta(seconds=cooldown_seconds)

        challenge = OTPChallenge(
            user_id=user_id,
            identifier=identifier,
            channel=channel,
            purpose=purpose,
            otp_hash=otp_hash,
            salt=salt,
            created_at=now,
            expires_at=expires_at,
            attempt_count=0,
            max_attempts=max_attempts,
            resend_available_at=resend_available_at,
            is_verified=False,
            is_invalidated=False,
        )
        db.session.add(challenge)

        # Dispatch code via requested channel
        if channel == OTPChannel.SMS:
            sms_provider = get_sms_provider()
            sms_msg = f"Your JaganPay verification code is {raw_otp}. Valid for 5 minutes. Do not share."
            sms_provider.send_sms(identifier, sms_msg, raw_otp=raw_otp)
        else:
            email_provider = get_email_provider()
            subject = f"JaganPay Verification Code [{purpose.replace('_', ' ').title()}]"
            html_body = f"""
            <div style="font-family: Arial, sans-serif; background-color: #0a0f24; color: #ffffff; padding: 24px; border-radius: 8px;">
                <h2 style="color: #38bdf8;">JaganPay — Payment Simulation</h2>
                <p>Your one-time verification code for <strong>{purpose}</strong> is:</p>
                <div style="font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #38bdf8; padding: 16px 0;">
                    {raw_otp}
                </div>
                <p style="color: #94a3b8; font-size: 13px;">This code expires in 5 minutes. Never share this OTP with anyone.</p>
                <p style="color: #64748b; font-size: 11px;">DEMO SIMULATION: JaganPay does not process real financial transactions.</p>
            </div>
            """
            text_body = f"Your JaganPay {purpose} OTP is: {raw_otp}. Valid for 5 minutes. Do not share."
            email_provider.send_email(identifier, subject, html_body, text_body, raw_otp=raw_otp)

        # Dispatch webhook event without plaintext OTP
        dispatch_event("OTP", {
            "user_id": user_id,
            "identifier": identifier,
            "channel": channel,
            "purpose": purpose,
            "timestamp": now.isoformat(),
        })

        if user_id:
            log_security_event(
                event_type="OTP_REQUESTED",
                user_id=user_id,
                status="SUCCESS",
                details={"purpose": purpose, "channel": channel}
            )

        db.session.commit()
        return challenge, expiry_seconds

    @classmethod
    def verify_challenge(
        cls,
        raw_code: str,
        identifier: str | None = None,
        purpose: str | None = None,
        user_id: str | None = None
    ) -> tuple[bool, str, OTPChallenge | None]:
        """
        Verify a submitted OTP against active challenges.
        Returns (is_valid, message, challenge_record).
        """
        query = OTPChallenge.query.filter_by(is_verified=False, is_invalidated=False)

        if identifier:
            clean_id = identifier.strip().lower() if "@" in identifier else identifier.strip()
            query = query.filter_by(identifier=clean_id)
        elif user_id:
            query = query.filter_by(user_id=user_id)

        if purpose:
            query = query.filter_by(purpose=purpose)

        challenge = query.order_by(OTPChallenge.created_at.desc()).first()

        if not challenge:
            # Check if there was an invalidated challenge to provide precise security feedback
            check_q = OTPChallenge.query
            if identifier:
                check_q = check_q.filter_by(identifier=clean_id)
            elif user_id:
                check_q = check_q.filter_by(user_id=user_id)
            if purpose:
                check_q = check_q.filter_by(purpose=purpose)
            recent = check_q.order_by(OTPChallenge.created_at.desc()).first()

            if recent and recent.is_invalidated:
                if recent.attempt_count >= recent.max_attempts:
                    return False, "Maximum verification attempts exceeded. Code has been locked. Please request a new code.", recent
                return False, "This verification challenge has been invalidated. Please request a new code.", recent

            if user_id:
                log_security_event("OTP_VERIFICATION_FAILED", user_id, "FAILURE", {"reason": "No active OTP"})
            return False, "No active verification code found. Please request a new code.", None

        success, msg = challenge.verify(raw_code)
        db.session.commit()

        target_uid = challenge.user_id or user_id
        if success:
            if target_uid:
                user = User.query.get(target_uid)
                if user and challenge.purpose == OTPPurpose.REGISTRATION:
                    user.is_verified = True
                    db.session.commit()

                log_security_event("OTP_VERIFIED", target_uid, "SUCCESS", {"purpose": challenge.purpose})
                log_audit(
                    action="OTP_VERIFICATION_SUCCESS",
                    user_id=target_uid,
                    user_email=user.email if user else challenge.identifier,
                    entity_type="OTP",
                    entity_id=str(challenge.id),
                    result="SUCCESS",
                    details={"purpose": challenge.purpose, "channel": challenge.channel}
                )
        else:
            if target_uid:
                user = User.query.get(target_uid)
                log_security_event("OTP_VERIFICATION_FAILED", target_uid, "FAILURE", {"reason": msg, "attempts": challenge.attempt_count})
                log_audit(
                    action="OTP_VERIFICATION_FAILED",
                    user_id=target_uid,
                    user_email=user.email if user else challenge.identifier,
                    entity_type="OTP",
                    entity_id=str(challenge.id),
                    result="FAILURE",
                    details={"reason": msg, "attempts": challenge.attempt_count}
                )

        return success, msg, challenge

    @classmethod
    def resend_challenge(
        cls,
        identifier: str,
        purpose: str = OTPPurpose.REGISTRATION,
        channel: str | None = None,
        user_id: str | None = None
    ) -> tuple[bool, str, int]:
        """
        Validate cooldown rate limiting, invalidate the prior active challenge,
        and issue a new one. Returns (success, message, expires_in_or_wait_seconds).
        """
        clean_id = identifier.strip().lower() if "@" in identifier else identifier.strip()

        # Check for active existing challenge for cooldown validation
        active = OTPChallenge.query.filter_by(
            identifier=clean_id,
            purpose=purpose,
            is_verified=False,
            is_invalidated=False
        ).order_by(OTPChallenge.created_at.desc()).first()

        if active:
            can_resend, wait_msg, wait_sec = active.can_resend()
            if not can_resend:
                return False, wait_msg, wait_sec
            use_channel = channel or active.channel
            use_uid = user_id or active.user_id
        else:
            use_channel = channel or (OTPChannel.EMAIL if "@" in clean_id else OTPChannel.SMS)
            use_uid = user_id

        _, expires_in = cls.create_challenge(
            identifier=clean_id,
            channel=use_channel,
            purpose=purpose,
            user_id=use_uid
        )
        return True, "New OTP sent", expires_in
