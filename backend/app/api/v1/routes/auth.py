from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.audit import record_audit_event
from app.core.errors import UnauthenticatedError
from app.core.ratelimit import rate_limit_dependency
from app.core.security import create_access_token, verify_password
from app.db.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(rate_limit_dependency)])
def login(
    request: Request,
    credentials: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    ip_addr = request.client.host if request.client else None
    user = db.query(User).filter(User.email == credentials.email).first()

    valid_password = verify_password(credentials.password, user.hashed_password) if user else False
    if not user or not user.is_active or not valid_password:
        record_audit_event(
            db,
            action="LOGIN_FAILED",
            user_email=credentials.email,
            ip_address=ip_addr,
            details={"reason": "invalid_credentials_or_inactive"},
        )
        raise UnauthenticatedError("Invalid email or password.")

    roles = [r.role_name for r in user.roles]
    token = create_access_token(user_id=user.id, email=user.email, roles=roles)

    record_audit_event(
        db,
        action="LOGIN_SUCCESS",
        user_id=user.id,
        user_email=user.email,
        ip_address=ip_addr,
    )

    return TokenResponse(access_token=token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    roles = [r.role_name for r in current_user.roles]
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        roles=roles,
        created_at=current_user.created_at,
    )
