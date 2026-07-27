from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import create_access_token, hash_password
from app.db.models.domain import InventorySnapshot, Material, Plant
from app.db.models.user import RoleEnum, User, UserRole
from app.services.planning.availability import calculate_planning_availability
from app.services.planning.engine import evaluate_material_planning
from app.services.planning.safety_stock import calculate_safety_stock


def _seed_user(db: Session, email: str, role_name: str) -> User:
    user = User(
        email=email,
        full_name=f"Release User {email}",
        hashed_password=hash_password("Pass123!"),
        is_active=True,
    )
    db.add(user)
    db.flush()
    role = UserRole(user_id=user.id, role_name=role_name)
    db.add(role)
    db.commit()
    db.refresh(user)
    return user


def _auth_header(user: User) -> dict[str, str]:
    roles = [r.role_name for r in user.roles]
    token = create_access_token(user_id=user.id, email=user.email, roles=roles)
    return {"Authorization": f"Bearer {token}"}


def test_production_configuration_safety():
    # Production mode with default dev secret key MUST fail validation
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            database_url="postgresql+psycopg://spip_user:spip_dev_password@db:5432/spip_db",
            app_env="production",
            secret_key="dev_secret_key_change_in_production_min_32_bytes_long_string",
        )
    assert "In production mode" in str(exc_info.value)

    # Valid production settings with custom key succeeds and disables OpenAPI docs URL
    prod_settings = Settings(
        database_url="postgresql+psycopg://spip_user:spip_dev_password@db:5432/spip_db",
        app_env="production",
        secret_key="custom_prod_secret_key_that_is_very_secure_and_long_enough",
    )
    assert prod_settings.openapi_url is None


def test_cors_preflight_login_allowed_origin(client):
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    response = client.options("/api/v1/auth/login", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"



def test_rbac_matrix_enforcement(client, db_session: Session):
    _seed_user(db_session, "rel_admin@spip.local", RoleEnum.ADMIN.value)
    planner = _seed_user(db_session, "rel_planner@spip.local", RoleEnum.PLANNER.value)
    manager = _seed_user(db_session, "rel_mgr@spip.local", RoleEnum.MANAGER_APPROVER.value)
    readonly = _seed_user(db_session, "rel_ro@spip.local", RoleEnum.READ_ONLY.value)

    plant = Plant(code="PLANT-REL", name="Release Plant")
    material = Material(code="MAT-REL", description="Release Material", base_uom="KG")
    db_session.add_all([plant, material])
    db_session.commit()

    inv = InventorySnapshot(
        plant_id=plant.id,
        material_id=material.id,
        snapshot_date=date.today(),
        usable_physical_stock=100.0,
        uom="KG",
    )
    db_session.add(inv)
    db_session.commit()

    alloc_payload = {
        "plant_code": "PLANT-REL",
        "material_code": "MAT-REL",
        "allocated_quantity": 10.0,
    }

    # 1. Read-only user CANNOT create allocations (HTTP 403)
    res_ro = client.post("/api/v1/allocations", json=alloc_payload, headers=_auth_header(readonly))
    assert res_ro.status_code == 403

    # 2. Planner CAN create allocation
    h_planner = _auth_header(planner)
    res_planner = client.post("/api/v1/allocations", json=alloc_payload, headers=h_planner)
    assert res_planner.status_code == 200
    alloc_id = res_planner.json()["id"]

    # 3. Planner CANNOT approve allocation (HTTP 403)
    res_p_approve = client.post(f"/api/v1/allocations/{alloc_id}/approve", headers=h_planner)
    assert res_p_approve.status_code == 403

    # 4. Manager CAN approve allocation
    h_mgr = _auth_header(manager)
    client.post(f"/api/v1/allocations/{alloc_id}/submit", headers=h_planner)
    res_m_approve = client.post(f"/api/v1/allocations/{alloc_id}/approve", headers=h_mgr)
    assert res_m_approve.status_code == 200
    assert res_m_approve.json()["status"] == "APPROVED"


def test_business_rules_and_calculation_integrity(db_session: Session):
    plant = Plant(code="PLANT-CALC", name="Calc Plant")
    material = Material(code="MAT-CALC", description="Calc Material", base_uom="KG")
    db_session.add_all([plant, material])
    db_session.commit()

    inv = InventorySnapshot(
        plant_id=plant.id,
        material_id=material.id,
        snapshot_date=date.today(),
        usable_physical_stock=200.0,
        uom="KG",
    )
    db_session.add(inv)
    db_session.commit()

    # 1. Safety Stock equation test: SS = Z * sigma_d * sqrt(LT)
    ss_res = calculate_safety_stock(
        demand_std_dev=10.0,
        lead_time_days=9.0,
    )
    assert ss_res.safety_stock == 49.5  # 1.65 * 10.0 * sqrt(9.0) = 49.5

    # 2. Planning Availability test: AI = usable + incoming_po - committed
    avail = calculate_planning_availability(db_session, plant.id, material.id)
    assert avail.planning_availability == 200.0

    # 3. Planning Decision Engine Criticality test
    plan_res = evaluate_material_planning(db_session, "PLANT-CALC", "MAT-CALC")
    assert plan_res.planning_availability == 200.0
    assert plan_res.criticality_status in ("CRITICAL", "WARNING", "HEALTHY")
