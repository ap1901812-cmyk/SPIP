from __future__ import annotations

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.ratelimit import MemoryRateLimiter
from app.core.security import create_access_token, hash_password
from app.db.models.audit import AuditLog
from app.db.models.user import RoleEnum, User, UserRole
from app.main import app


def _seed_test_users(db: Session) -> dict[str, User]:
    planner = User(
        email="planner@spip.local",
        full_name="Planner User",
        hashed_password=hash_password("PlannerPass123!"),
        is_active=True,
    )
    planner.roles.append(UserRole(role_name=RoleEnum.PLANNER.value))

    manager = User(
        email="manager@spip.local",
        full_name="Manager User",
        hashed_password=hash_password("ManagerPass123!"),
        is_active=True,
    )
    manager.roles.append(UserRole(role_name=RoleEnum.MANAGER_APPROVER.value))

    inactive = User(
        email="inactive@spip.local",
        full_name="Inactive User",
        hashed_password=hash_password("InactivePass123!"),
        is_active=False,
    )

    db.add_all([planner, manager, inactive])
    db.commit()
    db.refresh(planner)
    db.refresh(manager)
    db.refresh(inactive)
    return {"planner": planner, "manager": manager, "inactive": inactive}


def test_login_successful(client: TestClient, db_session: Session) -> None:
    users = _seed_test_users(db_session)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": users["planner"].email, "password": "PlannerPass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    audit_entry = db_session.query(AuditLog).filter(AuditLog.action == "LOGIN_SUCCESS").first()
    assert audit_entry is not None
    assert audit_entry.user_email == users["planner"].email


def test_login_failed_wrong_password(client: TestClient, db_session: Session) -> None:
    users = _seed_test_users(db_session)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": users["planner"].email, "password": "WrongPassword"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"

    audit_entry = db_session.query(AuditLog).filter(AuditLog.action == "LOGIN_FAILED").first()
    assert audit_entry is not None


def test_login_failed_inactive_user(client: TestClient, db_session: Session) -> None:
    users = _seed_test_users(db_session)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": users["inactive"].email, "password": "InactivePass123!"},
    )
    assert response.status_code == 401


def test_get_current_user_me_endpoint(client: TestClient, db_session: Session) -> None:
    users = _seed_test_users(db_session)
    token = create_access_token(
        user_id=users["planner"].id,
        email=users["planner"].email,
        roles=[RoleEnum.PLANNER.value],
    )

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == users["planner"].email
    assert data["full_name"] == "Planner User"
    assert RoleEnum.PLANNER.value in data["roles"]


def test_get_me_missing_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"


def test_get_me_invalid_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.str"})
    assert response.status_code == 401


def test_get_me_expired_token(client: TestClient, db_session: Session) -> None:
    users = _seed_test_users(db_session)
    expired_token = create_access_token(
        user_id=users["planner"].id,
        email=users["planner"].email,
        roles=[RoleEnum.PLANNER.value],
        expires_minutes=-5,
    )
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401


# Temporary test route for RBAC checks
manager_rbac_dep = Depends(require_roles(RoleEnum.MANAGER_APPROVER))


@app.get("/api/v1/test-rbac-manager", dependencies=[manager_rbac_dep])
def _test_rbac_manager_route() -> dict[str, str]:
    return {"message": "Manager approved route"}


def test_rbac_allowed_case(client: TestClient, db_session: Session) -> None:
    users = _seed_test_users(db_session)
    token = create_access_token(
        user_id=users["manager"].id,
        email=users["manager"].email,
        roles=[RoleEnum.MANAGER_APPROVER.value],
    )
    response = client.get(
        "/api/v1/test-rbac-manager", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Manager approved route"}


def test_rbac_forbidden_case(client: TestClient, db_session: Session) -> None:
    users = _seed_test_users(db_session)
    token = create_access_token(
        user_id=users["planner"].id,
        email=users["planner"].email,
        roles=[RoleEnum.PLANNER.value],
    )
    response = client.get(
        "/api/v1/test-rbac-manager", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_rate_limiting_trigger() -> None:
    MemoryRateLimiter.clear()
    for _ in range(5):
        MemoryRateLimiter.check_rate_limit("127.0.0.1", limit_per_minute=5)

    try:
        MemoryRateLimiter.check_rate_limit("127.0.0.1", limit_per_minute=5)
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 429
        return
    raise AssertionError("Rate limit did not trigger 429 exception")
