import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "jaganpay-fallback-secret-2026")
    DEMO_MODE = os.environ.get("DEMO_MODE", "True").lower() in ("true", "1", "yes")

    # OTP Provider Architecture
    OTP_PROVIDER_MODE = os.environ.get("OTP_PROVIDER_MODE", "mock")  # "mock" or "production"
    SMS_PROVIDER = os.environ.get("SMS_PROVIDER", "mock")
    SMS_API_KEY = os.environ.get("SMS_API_KEY", "")
    EMAIL_PROVIDER = os.environ.get("EMAIL_PROVIDER", "smtp")
    SMTP_FROM_EMAIL = os.environ.get("SMTP_FROM_EMAIL", "JaganPay Verification <noreply@jaganpay.local>")
    OTP_EXPIRY_SECONDS = int(os.environ.get("OTP_EXPIRY_SECONDS", 300))
    OTP_MAX_ATTEMPTS = int(os.environ.get("OTP_MAX_ATTEMPTS", 5))
    OTP_RESEND_COOLDOWN_SECONDS = int(os.environ.get("OTP_RESEND_COOLDOWN_SECONDS", 30))

    # Database
    db_url = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'jaganpay.db'}")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }

    # Session & Cookie Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False  # Set to True in ProductionConfig
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours

    # Rate Limiting
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    RATELIMIT_STORAGE_URI = "memory://"

    # AI Integration
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

    # Sensitive Action OTP Threshold
    SENSITIVE_TRANSACTION_THRESHOLD = float(os.environ.get("SENSITIVE_TRANSACTION_THRESHOLD", 10000.0))

    # SMTP Configuration
    SMTP_HOST = os.environ.get("SMTP_HOST", "localhost")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", 1025))
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "False").lower() in ("true", "1", "yes")
    MAIL_DEFAULT_SENDER = SMTP_FROM_EMAIL

    # n8n Webhook URLs
    N8N_BASE_URL = os.environ.get("N8N_BASE_URL", "http://localhost:5678")
    N8N_WEBHOOKS = {
        "REGISTRATION": os.environ.get("N8N_WEBHOOK_REGISTRATION", "http://localhost:5678/webhook/jaganpay-registration"),
        "OTP": os.environ.get("N8N_WEBHOOK_OTP", "http://localhost:5678/webhook/jaganpay-otp"),
        "PAYMENT_SUCCESS": os.environ.get("N8N_WEBHOOK_PAYMENT_SUCCESS", "http://localhost:5678/webhook/jaganpay-payment-success"),
        "PAYMENT_FAILURE": os.environ.get("N8N_WEBHOOK_PAYMENT_FAILURE", "http://localhost:5678/webhook/jaganpay-payment-failure"),
        "RISK_ALERT": os.environ.get("N8N_WEBHOOK_RISK_ALERT", "http://localhost:5678/webhook/jaganpay-risk-alert"),
        "DAILY_SUMMARY": os.environ.get("N8N_WEBHOOK_DAILY_SUMMARY", "http://localhost:5678/webhook/jaganpay-daily-summary"),
        "SUPPORT": os.environ.get("N8N_WEBHOOK_SUPPORT", "http://localhost:5678/webhook/jaganpay-support"),
        "ADMIN_REPORT": os.environ.get("N8N_WEBHOOK_ADMIN_REPORT", "http://localhost:5678/webhook/jaganpay-admin-report"),
    }


class DevelopmentConfig(Config):
    DEBUG = True
    ENV = "development"


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    OTP_PROVIDER_MODE = "mock"


class ProductionConfig(Config):
    DEBUG = False
    ENV = "production"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False").lower() in ("true", "1", "yes")
    OTP_PROVIDER_MODE = os.environ.get("OTP_PROVIDER_MODE", "mock" if not os.environ.get("SMS_API_KEY") else "production")



config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
