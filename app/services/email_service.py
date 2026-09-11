import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app

logger = logging.getLogger("jaganpay.email")


def send_email(to_email: str, subject: str, html_content: str, text_content: str = "") -> bool:
    """
    Send an email via configured SMTP or fallback to console simulation.
    Ensures zero crashes if SMTP server is unavailable.
    """
    app = current_app._get_current_object()
    smtp_host = app.config.get("SMTP_HOST", "localhost")
    smtp_port = app.config.get("SMTP_PORT", 1025)
    smtp_user = app.config.get("SMTP_USERNAME", "")
    smtp_pass = app.config.get("SMTP_PASSWORD", "")
    smtp_tls = app.config.get("SMTP_USE_TLS", False)
    default_sender = app.config.get("MAIL_DEFAULT_SENDER", "JaganPay <noreply@jaganpay.local>")

    # If no real credentials provided, simulate delivery cleanly
    if not smtp_user or smtp_host in ("localhost", "127.0.0.1"):
        logger.info(f"[SIMULATED EMAIL] To: {to_email} | Subject: {subject}")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = default_sender
        msg["To"] = to_email

        if text_content:
            msg.attach(MIMEText(text_content, "plain"))
        if html_content:
            msg.attach(MIMEText(html_content, "html"))

        server = smtplib.SMTP(smtp_host, smtp_port, timeout=5)
        if smtp_tls:
            server.starttls()
        if smtp_user and smtp_pass:
            server.login(smtp_user, smtp_pass)
        server.sendmail(default_sender, [to_email], msg.as_string())
        server.quit()
        logger.info(f"Email successfully delivered to {to_email}")
        return True
    except Exception as e:
        logger.warning(f"Failed to deliver SMTP email to {to_email}: {str(e)}. Continuing in simulation mode.")
        return False
