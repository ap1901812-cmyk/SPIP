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


def test_planning_api_unauthenticated(client: TestClient) -> None:
    res = client.get("/api/v1/planning/materials/MAT-1001?plant_code=PLANT-1000")
    assert res.status_code == 401


def test_planning_api_authenticated_material_evaluation(
    client: TestClient, db_session: Session
) -> None:
    token = _seed_user(db_session, "planner_eval@spip.local", RoleEnum.PLANNER.value)
    MockSAPAdapter().sync_to_database(db_session)

    res = client.get(
        "/api/v1/planning/materials/MAT-1001?plant_code=PLANT-1000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["plant_code"] == "PLANT-1000"
    assert data["material_code"] == "MAT-1001"
    assert "average_daily_demand" in data
    assert "safety_stock" in data
    assert "planning_availability" in data
    assert "reorder_point" in data
    assert data["criticality_status"] in ["CRITICAL", "WARNING", "HEALTHY"]
    assert "explanation" in data


def test_planning_api_nonexistent_material(client: TestClient, db_session: Session) -> None:
    token = _seed_user(db_session, "planner_nonexist@spip.local", RoleEnum.PLANNER.value)
    MockSAPAdapter().sync_to_database(db_session)

    res = client.get(
        "/api/v1/planning/materials/MAT-INVALID?plant_code=PLANT-1000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404
    assert res.json()["code"] == "PLANNING_ENGINE_ERROR"


def test_planning_summary_api(client: TestClient, db_session: Session) -> None:
    token = _seed_user(db_session, "planner_summary@spip.local", RoleEnum.PLANNER.value)
    MockSAPAdapter().sync_to_database(db_session)

    res = client.get(
        "/api/v1/planning/summary?plant_code=PLANT-1000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    summary = res.json()
    assert len(summary) > 0
    assert summary[0]["plant_code"] == "PLANT-1000"
