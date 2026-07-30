from __future__ import annotations

from collections.abc import Callable, Generator
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import UnauthenticatedError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.models.user import RoleEnum, User
from app.db.session import get_db_session

security_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    yield from get_db_session()


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)],
) -> User:
    if not credentials or not credentials.credentials:
        raise UnauthenticatedError("Authentication credentials were not provided or are invalid.")

    token = credentials.credentials
    payload = decode_access_token(token)

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthenticatedError("Invalid token subject.")

    try:
        user_id = int(user_id_str)
    except ValueError as exc:
        raise UnauthenticatedError("Invalid user ID in token.") from exc

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UnauthenticatedError("User account not found.")

    if not user.is_active:
        raise UnauthenticatedError("User account is inactive.")

    return user


def require_roles(*allowed_roles: RoleEnum | str) -> Callable[[User], User]:
    allowed_role_strs = {r.value if isinstance(r, RoleEnum) else r for r in allowed_roles}
    if RoleEnum.MANAGER_APPROVER.value in allowed_role_strs or "Manager" in allowed_role_strs:
        allowed_role_strs.add("Manager")
        allowed_role_strs.add(RoleEnum.MANAGER_APPROVER.value)

    def role_checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        user_role_names = {r.role_name for r in current_user.roles}
        if RoleEnum.ADMIN.value in user_role_names:
            return current_user

        if not user_role_names.intersection(allowed_role_strs):
            raise UnauthorizedError("Insufficient permissions to perform this action.")

        return current_user

    return role_checker
