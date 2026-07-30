from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, validate_password_policy
from app.db.models.user import RoleEnum, User, UserRole


def _seed_admin_and_users(db: Session) -> dict[str, User]:
    admin = User(
        username="admin",
        email="admin@spip.local",
        full_name="Aditya Pandey",
        hashed_password=hash_password("Pass123!"),
        is_active=True,
        must_change_password=False,
    )
    admin.roles.append(UserRole(role_name=RoleEnum.ADMIN.value))

    planner = User(
        username="planner",
        email="planner@spip.local",
        full_name="Rahul Sharma",
        hashed_password=hash_password("Pass123!"),
        is_active=True,
        must_change_password=False,
    )
    planner.roles.append(UserRole(role_name=RoleEnum.PLANNER.value))

    db.add_all([admin, planner])
    db.commit()
    db.refresh(admin)
    db.refresh(planner)
    return {"admin": admin, "planner": planner}


def test_password_policy_validation() -> None:
    # Valid
    validate_password_policy("StrongP@ss1")

    # Too short
    try:
        validate_password_policy("Sh0r!t")
        assert False, "Should have failed policy"
    except ValueError as e:
        assert "at least 8 characters" in str(e)

    # Missing uppercase
    try:
        validate_password_policy("weakp@ss1")
        assert False, "Should have failed policy"
    except ValueError as e:
        assert "uppercase" in str(e)

    # Missing digit
    try:
        validate_password_policy("WeakP@ssword")
        assert False, "Should have failed policy"
    except ValueError as e:
        assert "digit" in str(e)

    # Missing special char
    try:
        validate_password_policy("WeakPass123")
        assert False, "Should have failed policy"
    except ValueError as e:
        assert "special character" in str(e)


def test_username_only_login(client: TestClient, db_session: Session) -> None:
    users = _seed_admin_and_users(db_session)
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "Pass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["must_change_password"] is False


def test_admin_create_user(client: TestClient, db_session: Session) -> None:
    users = _seed_admin_and_users(db_session)
    token = create_access_token(user_id=users["admin"].id, email=users["admin"].email, roles=[RoleEnum.ADMIN.value])

    # Create new user with custom password
    payload = {
        "username": "amit_v",
        "email": "amit@spip.local",
        "full_name": "Amit Verma",
        "password": "TempPass123!",
        "roles": ["Manager"],
        "is_active": True,
    }
    res = client.post("/api/v1/users", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 201
    data = res.json()
    assert data["username"] == "amit_v"
    assert data["full_name"] == "Amit Verma"
    assert RoleEnum.MANAGER_APPROVER.value in data["roles"]
    assert data["must_change_password"] is True


def test_admin_create_user_auto_generate_password(client: TestClient, db_session: Session) -> None:
    users = _seed_admin_and_users(db_session)
    token = create_access_token(user_id=users["admin"].id, email=users["admin"].email, roles=[RoleEnum.ADMIN.value])

    payload = {
        "username": "auto_user",
        "email": "auto@spip.local",
        "full_name": "Auto Generated Password User",
        "roles": ["Planner"],
        "is_active": True,
    }
    res = client.post("/api/v1/users", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 201
    data = res.json()
    assert data["username"] == "auto_user"
    assert data["must_change_password"] is True


def test_admin_create_user_duplicate_username(client: TestClient, db_session: Session) -> None:
    users = _seed_admin_and_users(db_session)
    token = create_access_token(user_id=users["admin"].id, email=users["admin"].email, roles=[RoleEnum.ADMIN.value])

    payload = {
        "username": "admin",
        "email": "unique@spip.local",
        "full_name": "Duplicate Username User",
        "password": "TempPass123!",
        "roles": ["Planner"],
    }
    res = client.post("/api/v1/users", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400
    assert "Username already exists" in res.json()["message"]


def test_first_login_password_change_flow(client: TestClient, db_session: Session) -> None:
    users = _seed_admin_and_users(db_session)
    admin_token = create_access_token(user_id=users["admin"].id, email=users["admin"].email, roles=[RoleEnum.ADMIN.value])

    # 1. Admin creates user
    res = client.post(
        "/api/v1/users",
        json={
            "username": "newuser",
            "email": "newuser@spip.local",
            "full_name": "New User",
            "password": "InitialTemp123!",
            "roles": ["Planner"],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 201

    # 2. User logs in
    login_res = client.post("/api/v1/auth/login", json={"username": "newuser", "password": "InitialTemp123!"})
    assert login_res.status_code == 200
    user_token = login_res.json()["access_token"]
    assert login_res.json()["must_change_password"] is True

    # 3. User changes password
    change_pw_res = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "InitialTemp123!", "new_password": "NewSecurePassword123!"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert change_pw_res.status_code == 200

    # 4. Verify me endpoint returns must_change_password = False
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {user_token}"})
    assert me_res.status_code == 200
    assert me_res.json()["must_change_password"] is False


def test_admin_user_management_crud(client: TestClient, db_session: Session) -> None:
    users = _seed_admin_and_users(db_session)
    admin_token = create_access_token(user_id=users["admin"].id, email=users["admin"].email, roles=[RoleEnum.ADMIN.value])

    # List users
    list_res = client.get("/api/v1/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 2

    # Edit user
    planner_id = users["planner"].id
    edit_res = client.put(
        f"/api/v1/users/{planner_id}",
        json={"full_name": "Rahul Sharma Updated", "roles": ["Manager"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert edit_res.status_code == 200
    assert edit_res.json()["full_name"] == "Rahul Sharma Updated"

    # Reset password
    reset_res = client.post(
        f"/api/v1/users/{planner_id}/reset-password",
        json={"new_password": "NewResetPass123!"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert reset_res.status_code == 200

    # Deactivate user
    status_res = client.patch(
        f"/api/v1/users/{planner_id}/status",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert status_res.status_code == 200
    assert status_res.json()["is_active"] is False


def test_non_admin_forbidden_user_management(client: TestClient, db_session: Session) -> None:
    users = _seed_admin_and_users(db_session)
    planner_token = create_access_token(user_id=users["planner"].id, email=users["planner"].email, roles=[RoleEnum.PLANNER.value])

    res = client.get("/api/v1/users", headers={"Authorization": f"Bearer {planner_token}"})
    assert res.status_code == 403


def test_cannot_deactivate_last_admin(client: TestClient, db_session: Session) -> None:
    users = _seed_admin_and_users(db_session)
    admin_token = create_access_token(user_id=users["admin"].id, email=users["admin"].email, roles=[RoleEnum.ADMIN.value])

    res = client.patch(
        f"/api/v1/users/{users['admin'].id}/status",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 400
    assert "last remaining active Admin user" in res.json()["message"]
