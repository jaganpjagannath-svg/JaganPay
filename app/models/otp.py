import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from app.extensions import db


class OTPPurpose:
    REGISTRATION = "REGISTRATION"
    LOGIN = "LOGIN"
    SENSITIVE_ACTION = "SENSITIVE_ACTION"
    PIN_CHANGE = "PIN_CHANGE"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"


class OTPChannel:
    SMS = "SMS"
    EMAIL = "EMAIL"


class OTPChallenge(db.Model):
    __tablename__ = "otp_challenges"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    identifier = db.Column(db.String(120), nullable=False, index=True)  # phone number or email address
    channel = db.Column(db.String(10), nullable=False, default=OTPChannel.SMS)
    purpose = db.Column(db.String(32), nullable=False, default=OTPPurpose.REGISTRATION)
    otp_hash = db.Column(db.String(128), nullable=False)
    salt = db.Column(db.String(32), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    verified_at = db.Column(db.DateTime, nullable=True)
    attempt_count = db.Column(db.Integer, default=0, nullable=False)
    max_attempts = db.Column(db.Integer, default=5, nullable=False)
    resend_available_at = db.Column(db.DateTime, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    is_invalidated = db.Column(db.Boolean, default=False, nullable=False)

    user = db.relationship("User", backref=db.backref("otp_challenges", cascade="all, delete-orphan", lazy="dynamic"))

    @staticmethod
    def hash_otp(raw_otp: str, salt: str) -> str:
        """Salted SHA-256 hash for secure storage."""
        return hashlib.sha256((salt + raw_otp).encode("utf-8")).hexdigest()

    def verify(self, raw_candidate: str) -> tuple[bool, str]:
        """Verify the user-provided code using timing-safe comparison."""
        if self.is_invalidated:
            return False, "This verification challenge has been invalidated. Please request a new code."
        if self.is_verified:
            return False, "This verification code has already been used."
        if datetime.utcnow() > self.expires_at:
            self.is_invalidated = True
            return False, "This verification code has expired. Please request a new code."
        if self.attempt_count >= self.max_attempts:
            self.is_invalidated = True
            return False, "Maximum verification attempts exceeded. Code has been locked. Please request a new OTP."

        self.attempt_count += 1
        candidate_hash = self.hash_otp(raw_candidate.strip(), self.salt)

        # Constant-time comparison to prevent timing attacks
        if hmac.compare_digest(candidate_hash, self.otp_hash):
            self.is_verified = True
            self.verified_at = datetime.utcnow()
            return True, "Verification successful."

        if self.attempt_count >= self.max_attempts:
            self.is_invalidated = True
            return False, "Invalid verification code. Maximum attempts exceeded. Code has been locked."

        remaining = self.max_attempts - self.attempt_count
        return False, f"Invalid verification code. {remaining} attempt(s) remaining."

    def can_resend(self) -> tuple[bool, str, int]:
        """Check rate-limit cooldown before issuing another OTP."""
        now = datetime.utcnow()
        if now < self.resend_available_at:
            wait_seconds = max(1, int((self.resend_available_at - now).total_seconds()))
            return False, f"Please wait {wait_seconds} seconds before requesting another code.", wait_seconds
        return True, "Resend allowed.", 0


class OTPVerification(db.Model):
    """Legacy model maintained for backward compatibility."""
    __tablename__ = "otp_verifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    otp_hash = db.Column(db.String(128), nullable=False)
    salt = db.Column(db.String(32), nullable=False)
    purpose = db.Column(db.String(32), nullable=False, default=OTPPurpose.REGISTRATION)
    attempts = db.Column(db.Integer, default=0, nullable=False)
    max_attempts = db.Column(db.Integer, default=5, nullable=False)
    resend_count = db.Column(db.Integer, default=0, nullable=False)
    max_resends = db.Column(db.Integer, default=5, nullable=False)
    is_used = db.Column(db.Boolean, default=False, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_resend_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", backref=db.backref("otp_records", cascade="all, delete-orphan", lazy="dynamic"))

    @staticmethod
    def hash_otp(raw_otp: str, salt: str) -> str:
        return hashlib.sha256((salt + raw_otp).encode("utf-8")).hexdigest()
