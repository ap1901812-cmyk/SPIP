from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models.user import User
from app.schemas.notification import (
    NotificationListResponseSchema,
    NotificationResponseSchema,
    UnreadCountResponseSchema,
)
from app.services.notification.service import (
    get_unread_count,
    get_user_notifications,
    mark_all_notifications_as_read,
    mark_notification_as_read,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponseSchema)
def api_list_notifications(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    unread_only: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> NotificationListResponseSchema:
    items, total = get_user_notifications(
        db, user_id=current_user.id, unread_only=unread_only, limit=limit, offset=offset
    )
    return NotificationListResponseSchema(
        items=[NotificationResponseSchema.model_validate(n) for n in items],
        total=total,
    )


@router.get("/unread-count", response_model=UnreadCountResponseSchema)
def api_get_unread_count(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UnreadCountResponseSchema:
    count = get_unread_count(db, user_id=current_user.id)
    return UnreadCountResponseSchema(unread_count=count)


@router.patch("/{notification_id}/read", response_model=NotificationResponseSchema)
def api_mark_as_read(
    notification_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> NotificationResponseSchema:
    notif = mark_notification_as_read(
        db, user_id=current_user.id, notification_id=notification_id
    )
    return NotificationResponseSchema.model_validate(notif)


@router.post("/mark-all-read", response_model=UnreadCountResponseSchema)
def api_mark_all_read(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UnreadCountResponseSchema:
    mark_all_notifications_as_read(db, user_id=current_user.id)
    return UnreadCountResponseSchema(unread_count=0)
