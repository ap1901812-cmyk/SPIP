from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserBase(BaseModel):
    username: str = Field(..., description="User username")
    email: str = Field(..., description="User email address")
    full_name: str
    is_active: bool = True


class UserCreate(UserBase):
    password: str | None = None
    roles: list[str] = []


class UserUpdate(BaseModel):
    username: str | None = None
    full_name: str | None = None
    email: str | None = None
    roles: list[str] | None = None
    is_active: bool | None = None


class UserResetPassword(BaseModel):
    new_password: str | None = None


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    roles: list[str] = []
    must_change_password: bool = False
    created_at: datetime
