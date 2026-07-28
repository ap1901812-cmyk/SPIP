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


def test_v15_rbac_permissions_matrix(client: TestClient, db_session: Session) -> None:
    MockSAPAdapter().sync_to_database(db_session)

    admin_token = _seed_user(db_session, "admin_v15@spip.local", RoleEnum.ADMIN.value)
    planner_token = _seed_user(db_session, "planner_v15@spip.local", RoleEnum.PLANNER.value)
    manager_token = _seed_user(db_session, "manager_v15@spip.local", RoleEnum.MANAGER_APPROVER.value)
    readonly_token = _seed_user(db_session, "readonly_v15@spip.local", RoleEnum.READ_ONLY.value)

    # 1. GET endpoints: Accessible by all authenticated roles
    for token in [admin_token, planner_token, manager_token, readonly_token]:
        headers = {"Authorization": f"Bearer {token}"}
        assert client.get("/api/v1/finished-goods", headers=headers).status_code == 200
        assert client.get("/api/v1/boms", headers=headers).status_code == 200
        assert client.get("/api/v1/planning/shortages", headers=headers).status_code == 200
        assert client.get("/api/v1/planning/recommendations", headers=headers).status_code == 200

    # 2. POST /api/v1/boms: Allowed for Planner and Admin; forbidden for Manager and Readonly
    bom_payload = {
        "fg_material_id": 1,
        "component_material_id": 2,
        "required_quantity": 3.0,
        "unit_of_measure": "KG",
    }
    assert client.post("/api/v1/boms", json=bom_payload, headers={"Authorization": f"Bearer {readonly_token}"}).status_code == 403
    assert client.post("/api/v1/boms", json=bom_payload, headers={"Authorization": f"Bearer {manager_token}"}).status_code == 403

    # 3. POST /api/v1/planning/run: Allowed for Planner and Admin; forbidden for Manager and Readonly
    plan_payload = {"demands": []}
    assert client.post("/api/v1/planning/run", json=plan_payload, headers={"Authorization": f"Bearer {readonly_token}"}).status_code == 403
    assert client.post("/api/v1/planning/run", json=plan_payload, headers={"Authorization": f"Bearer {manager_token}"}).status_code == 403
    assert client.post("/api/v1/planning/run", json=plan_payload, headers={"Authorization": f"Bearer {planner_token}"}).status_code == 200
    assert client.post("/api/v1/planning/run", json=plan_payload, headers={"Authorization": f"Bearer {admin_token}"}).status_code == 200


def test_v15_error_handling_and_not_found(client: TestClient, db_session: Session) -> None:
    token = _seed_user(db_session, "planner_err@spip.local", RoleEnum.PLANNER.value)
    headers = {"Authorization": f"Bearer {token}"}

    # Request invalid FG detail
    res1 = client.get("/api/v1/finished-goods/99999", headers=headers)
    assert res1.status_code == 404

    # Request invalid material where-used
    res2 = client.get("/api/v1/materials/99999/where-used", headers=headers)
    assert res2.status_code == 404

    # Submit invalid FG code in planning run
    res3 = client.post(
        "/api/v1/planning/run",
        json={"demands": [{"fg_code": "INVALID-FG-CODE", "plant_code": "PLANT-1000", "demand_quantity": 10.0}]},
        headers=headers,
    )
    assert res3.status_code == 404



def test_v15_end_to_end_planning_integration(client: TestClient, db_session: Session) -> None:
    token = _seed_user(db_session, "e2e_planner@spip.local", RoleEnum.PLANNER.value)
    MockSAPAdapter().sync_to_database(db_session)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Fetch FG list
    fg_res = client.get("/api/v1/finished-goods", headers=headers)
    assert fg_res.status_code == 200
    fg_list = fg_res.json()
    assert len(fg_list) >= 1

    target_fg = fg_list[0]

    # 2. Fetch FG detail & BOM expansion
    detail_res = client.get(f"/api/v1/finished-goods/{target_fg['id']}", headers=headers)
    assert detail_res.status_code == 200

    bom_res = client.get(f"/api/v1/finished-goods/{target_fg['id']}/bom", headers=headers)
    assert bom_res.status_code == 200

    # 3. Run Planning calculation for target FG
    plan_req = {
        "demands": [
            {"fg_code": target_fg["code"], "plant_code": "PLANT-1000", "demand_quantity": 500.0}
        ]
    }
    plan_res = client.post("/api/v1/planning/run", json=plan_req, headers=headers)
    assert plan_res.status_code == 200
    plan_data = plan_res.json()

    assert "summary" in plan_data
    assert "component_requirements" in plan_data
    assert "procurement_recommendations" in plan_data
    assert "affected_finished_goods" in plan_data
    assert plan_data["summary"]["total_demand_items_evaluated"] == 1
