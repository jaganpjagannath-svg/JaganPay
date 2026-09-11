import logging
from app.extensions import db
from app.models.notification import Notification, NotificationType

logger = logging.getLogger("jaganpay.notifications")


def create_notification(
    user_id: str,
    title: str,
    message: str,
    notif_type: str = NotificationType.SYSTEM,
    reference_id: str = None
) -> Notification:
    try:
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=notif_type,
            reference_id=reference_id,
            is_read=False,
        )
        db.session.add(notif)
        db.session.commit()
        return notif
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to create notification for user {user_id}: {e}")
        return None
