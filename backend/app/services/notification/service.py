from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models.notification import Notification
from app.db.models.user import User
from app.services.notification.email import get_email_adapter

logger = logging.getLogger(__name__)


class NotificationError(AppError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__("NOTIFICATION_ERROR", message, status_code)


def create_notification(
    db: Session,
    recipient_user_id: int,
    notification_type: str,
    title: str,
    message: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    send_email: bool = True,
) -> Notification:
    """Creates persistent in-app notification and dispatches email via adapter."""
    user = db.query(User).filter(User.id == recipient_user_id).first()
    if not user:
        raise NotificationError(f"User with ID {recipient_user_id} not found.", 404)

    notif = Notification(
        user_id=recipient_user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        resource_type=resource_type,
        resource_id=resource_id,
        is_read=False,
    )
    db.add(notif)
    db.flush()

    if send_email and user.email:
        try:
            adapter = get_email_adapter()
            adapter.send_email(to_email=user.email, subject=title, body=message)
        except Exception:
            logger.exception("Failed to dispatch notification email to %s", user.email)

    return notif


def get_user_notifications(
    db: Session,
    user_id: int,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Notification], int]:
    """Retrieves paginated notifications for current user with recipient isolation."""
    query = db.query(Notification).filter(Notification.user_id == user_id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))

    total = query.count()
    items = query.order_by(Notification.id.desc()).offset(offset).limit(limit).all()
    return items, total


def get_unread_count(db: Session, user_id: int) -> int:
    """Gets total unread notification count for user."""
    return (
        db.query(func.count(Notification.id))
        .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
        .scalar()
        or 0
    )


def mark_notification_as_read(
    db: Session,
    user_id: int,
    notification_id: int,
) -> Notification:
    """Marks a single notification as read if owned by user."""
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notif:
        raise NotificationError(f"Notification with ID {notification_id} not found.", 404)

    if notif.user_id != user_id:
        raise NotificationError("Access denied to notification.", 403)

    if not notif.is_read:
        notif.is_read = True
        notif.read_at = datetime.now(UTC)
        db.add(notif)
        db.commit()
        db.refresh(notif)

    return notif


def mark_all_notifications_as_read(db: Session, user_id: int) -> int:
    """Marks all unread notifications for user as read."""
    now = datetime.now(UTC)
    count = (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
        .update({"is_read": True, "read_at": now}, synchronize_session=False)
    )
    db.commit()
    return count
