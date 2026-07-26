from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.db.models.user import RoleEnum, User, UserRole
from app.services.sap import MockSAPAdapter


def _seed_user(db: Session, email: str, role_name: str) -> str:
    user = User(
        email=email,
        full_name=f"{role_name} User",
        hashed_password=hash_password("Pass123!"),
        is_active=True,
    )
    user.roles.append(UserRole(role_name=role_name))
    db.add(user)
    db.commit()
    db.refresh(user)
    return create_access_token(user_id=user.id, email=user.email, roles=[role_name])


def test_allocation_api_unauthenticated(client: TestClient) -> None:
    res = client.get("/api/v1/allocations")
    assert res.status_code == 401


def test_allocation_api_lifecycle_and_rbac(client: TestClient, db_session: Session) -> None:
    MockSAPAdapter().sync_to_database(db_session)

    planner_token = _seed_user(db_session, "planner_alc_api@spip.local", RoleEnum.PLANNER.value)
    manager_token = _seed_user(
        db_session, "manager_alc_api@spip.local", RoleEnum.MANAGER_APPROVER.value
    )
    read_token = _seed_user(db_session, "read_alc_api@spip.local", RoleEnum.READ_ONLY.value)


    # 1. Read-only user cannot create allocation (403 Forbidden)
    res_forbidden = client.post(
        "/api/v1/allocations",
        json={
            "plant_code": "PLANT-1000",
            "material_code": "MAT-1001",
            "allocated_quantity": 100.0,
        },
        headers={"Authorization": f"Bearer {read_token}"},
    )
    assert res_forbidden.status_code == 403

    # 2. Planner creates allocation (200 OK)
    res_create = client.post(
        "/api/v1/allocations",
        json={
            "plant_code": "PLANT-1000",
            "material_code": "MAT-1001",
            "allocated_quantity": 100.0,
            "uom": "KG",
        },
        headers={"Authorization": f"Bearer {planner_token}"},
    )
    assert res_create.status_code == 200
    alloc_data = res_create.json()
    alloc_id = alloc_data["id"]
    assert alloc_data["status"] == "DRAFT"

    # 3. Planner submits allocation
    res_submit = client.post(
        f"/api/v1/allocations/{alloc_id}/submit",
        headers={"Authorization": f"Bearer {planner_token}"},
    )
    assert res_submit.status_code == 200
    assert res_submit.json()["status"] == "PENDING_APPROVAL"

    # 4. Planner CANNOT approve (403 Forbidden)
    res_plan_appr = client.post(
        f"/api/v1/allocations/{alloc_id}/approve",
        headers={"Authorization": f"Bearer {planner_token}"},
    )
    assert res_plan_appr.status_code == 403

    # 5. Manager approves allocation (200 OK)
    res_mgr_appr = client.post(
        f"/api/v1/allocations/{alloc_id}/approve",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert res_mgr_appr.status_code == 200
    assert res_mgr_appr.json()["status"] == "APPROVED"
    assert res_mgr_appr.json()["sap_reference_id"] is not None


def test_allocation_api_nonexistent_entity(client: TestClient, db_session: Session) -> None:
    planner_token = _seed_user(db_session, "planner_nonexist@spip.local", RoleEnum.PLANNER.value)
    res = client.get(
        "/api/v1/allocations/999999",
        headers={"Authorization": f"Bearer {planner_token}"},
    )
    assert res.status_code == 404
    assert res.json()["code"] == "ALLOCATION_ERROR"
