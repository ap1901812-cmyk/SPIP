from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserBase(BaseModel):
    email: str = Field(..., description="User email address")
    full_name: str
    is_active: bool = True


class UserCreate(UserBase):
    password: str
    roles: list[str] = []


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    roles: list[str] = []
    created_at: datetime
