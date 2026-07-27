from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    notification_type: str
    title: str
    message: str
    resource_type: str | None = None
    resource_id: str | None = None
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime


class UnreadCountResponseSchema(BaseModel):
    unread_count: int


class NotificationListResponseSchema(BaseModel):
    items: list[NotificationResponseSchema]
    total: int
