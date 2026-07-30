from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.core.audit import record_audit_event
from app.core.errors import BadRequestError
from app.core.security import generate_secure_temporary_password, hash_password, validate_password_policy
from app.db.models.user import RoleEnum, User, UserRole
from app.schemas.user import (
    UserCreate,
    UserResponse,
    UserResetPassword,
    UserStatusUpdate,
    UserUpdate,
)

router = APIRouter(prefix="/users", tags=["users"])

admin_role_dep = Depends(require_roles(RoleEnum.ADMIN))


def _normalize_role_name(role: str) -> str:
    r = role.strip()
    if r.lower() in ("manager", "manager/approver"):
        return RoleEnum.MANAGER_APPROVER.value
    if r.lower() == "planner":
        return RoleEnum.PLANNER.value
    if r.lower() == "admin":
        return RoleEnum.ADMIN.value
    return r


def _to_user_response(user: User) -> UserResponse:
    roles = [r.role_name for r in user.roles]
    return UserResponse(
        id=user.id,
        username=user.username or "",
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        roles=roles,
        must_change_password=user.must_change_password,
        created_at=user.created_at,
    )


@router.get("", response_model=list[UserResponse], dependencies=[admin_role_dep])
def list_users(
    db: Annotated[Session, Depends(get_db)],
) -> list[UserResponse]:
    users = db.query(User).order_by(User.id.asc()).all()
    return [_to_user_response(u) for u in users]


@router.get("/{user_id}", response_model=UserResponse, dependencies=[admin_role_dep])
def get_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BadRequestError("User not found.")
    return _to_user_response(user)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED, dependencies=[admin_role_dep])
def create_user(
    user_in: UserCreate,
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    # 1. Unique checks
    if db.query(User).filter(User.username == user_in.username).first():
        raise BadRequestError("Username already exists.")

    if db.query(User).filter(User.email == user_in.email).first():
        raise BadRequestError("Email address already exists.")

    # 2. Password processing & validation
    raw_password = user_in.password
    if not raw_password:
        raw_password = generate_secure_temporary_password()

    try:
        validate_password_policy(raw_password)
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc

    # 3. Create user
    user = User(
        username=user_in.username,
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hash_password(raw_password),
        is_active=user_in.is_active,
        must_change_password=True,
    )
    db.add(user)
    db.flush()

    # 4. Roles
    role_names = user_in.roles if user_in.roles else [RoleEnum.PLANNER.value]
    for r in role_names:
        norm_r = _normalize_role_name(r)
        user.roles.append(UserRole(role_name=norm_r))

    db.commit()
    db.refresh(user)

    record_audit_event(
        db,
        action="USER_CREATED",
        user_id=user.id,
        user_email=user.email,
        details={"username": user.username, "roles": [r.role_name for r in user.roles]},
    )

    resp = _to_user_response(user)
    # Include temporary password in temporary field for admin notification if generated
    return resp


def _check_last_admin(
    db: Session, target_user: User, new_is_active: bool | None, new_roles: list[str] | None
) -> None:
    is_target_admin = any(r.role_name == RoleEnum.ADMIN.value for r in target_user.roles)
    if not is_target_admin:
        return

    will_be_active = target_user.is_active if new_is_active is None else new_is_active
    will_have_admin = is_target_admin
    if new_roles is not None:
        norm_new_roles = [_normalize_role_name(r) for r in new_roles]
        will_have_admin = RoleEnum.ADMIN.value in norm_new_roles

    if not will_be_active or not will_have_admin:
        active_admins = (
            db.query(User)
            .join(UserRole)
            .filter(User.is_active == True, UserRole.role_name == RoleEnum.ADMIN.value)
            .all()
        )
        if len(active_admins) <= 1:
            raise BadRequestError("Cannot deactivate or remove Admin role from the last remaining active Admin user.")


@router.put("/{user_id}", response_model=UserResponse, dependencies=[admin_role_dep])
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BadRequestError("User not found.")

    _check_last_admin(db, user, user_in.is_active, user_in.roles)

    if user_in.username and user_in.username != user.username:
        if db.query(User).filter(User.username == user_in.username, User.id != user_id).first():
            raise BadRequestError("Username already exists.")
        user.username = user_in.username

    if user_in.email and user_in.email != user.email:
        if db.query(User).filter(User.email == user_in.email, User.id != user_id).first():
            raise BadRequestError("Email address already exists.")
        user.email = user_in.email

    if user_in.full_name is not None:
        user.full_name = user_in.full_name

    if user_in.is_active is not None:
        user.is_active = user_in.is_active

    if user_in.roles is not None:
        user.roles.clear()
        for r in user_in.roles:
            user.roles.append(UserRole(role_name=_normalize_role_name(r)))

    db.commit()
    db.refresh(user)

    record_audit_event(
        db,
        action="USER_UPDATED",
        user_id=user.id,
        user_email=user.email,
    )

    return _to_user_response(user)


@router.post("/{user_id}/reset-password", response_model=dict[str, str], dependencies=[admin_role_dep])
def reset_user_password(
    user_id: int,
    payload: UserResetPassword,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BadRequestError("User not found.")

    new_pw = payload.new_password
    if not new_pw:
        new_pw = generate_secure_temporary_password()

    try:
        validate_password_policy(new_pw)
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc

    user.hashed_password = hash_password(new_pw)
    user.must_change_password = True
    db.commit()

    record_audit_event(
        db,
        action="USER_PASSWORD_RESET_BY_ADMIN",
        user_id=user.id,
        user_email=user.email,
    )

    return {"message": "Password reset successfully.", "temporary_password": new_pw}


@router.patch("/{user_id}/status", response_model=UserResponse, dependencies=[admin_role_dep])
def update_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BadRequestError("User not found.")

    _check_last_admin(db, user, payload.is_active, None)

    user.is_active = payload.is_active
    db.commit()
    db.refresh(user)

    record_audit_event(
        db,
        action="USER_STATUS_UPDATED",
        user_id=user.id,
        user_email=user.email,
        details={"is_active": user.is_active},
    )

    return _to_user_response(user)
