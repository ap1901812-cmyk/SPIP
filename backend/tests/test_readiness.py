from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.db.models.audit import AuditLog
from app.db.models.domain import (
    ConsumptionHistory,
    InventorySnapshot,
    Material,
    Plant,
    PlantMaterial,
    PlanningReadinessScore,
)
from app.db.models.user import RoleEnum, User, UserRole
from app.services.planning.readiness import (
    PlanningReadinessEngine,
    ReadinessStateEnum,
)


def _seed_planner(db: Session) -> dict[str, str]:
    user = User(
        email="planner_readiness@example.com",
        full_name="Readiness Planner User",
        hashed_password=hash_password("Pass123!"),
        is_active=True,
    )
    user.roles.append(UserRole(role_name=RoleEnum.PLANNER.value))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user_id=user.id, email=user.email, roles=[RoleEnum.PLANNER.value])
    return {"Authorization": f"Bearer {token}"}


def test_readiness_blocked_state(db_session: Session) -> None:
    plant = Plant(code="PLANT-BLOCKED", name="Blocked Plant")
    db_session.add(plant)
    db_session.commit()

    engine = PlanningReadinessEngine(db=db_session)
    report = engine.evaluate_readiness("PLANT-BLOCKED")

    assert report.readiness_state == ReadinessStateEnum.BLOCKED
    assert report.can_proceed_to_planning is False
    assert report.score < 50.0
    assert len(report.blocking_issues) >= 2  # Missing Stock & Consumption


def test_readiness_ready_with_warnings_state(db_session: Session) -> None:
    plant = Plant(code="PLANT-WARN", name="Warn Plant")
    material = Material(code="MAT-WARN-1", description="Material 1", base_uom="KG")
    db_session.add_all([plant, material])
    db_session.commit()

    # Add mandatory Stock and Consumption
    stock = InventorySnapshot(
        plant_id=plant.id, material_id=material.id, snapshot_date=date.today(), usable_physical_stock=500.0, uom="KG"
    )
    cons = ConsumptionHistory(
        plant_id=plant.id, material_id=material.id, consumption_date=date.today(), quantity=50.0, uom="KG"
    )
    pm = PlantMaterial(plant_id=plant.id, material_id=material.id)  # Missing lead_time_1/safety_stock_1
    db_session.add_all([stock, cons, pm])
    db_session.commit()

    engine = PlanningReadinessEngine(db=db_session)
    report = engine.evaluate_readiness("PLANT-WARN")

    assert report.readiness_state == ReadinessStateEnum.READY_WITH_WARNINGS
    assert report.can_proceed_to_planning is True
    assert len(report.blocking_issues) == 0
    assert len(report.warnings) >= 1  # Missing RMPM params


def test_planner_acknowledgement_flow(db_session: Session) -> None:
    plant = Plant(code="PLANT-ACK", name="Ack Plant")
    material = Material(code="MAT-ACK-1", description="Material Ack", base_uom="KG")
    db_session.add_all([plant, material])
    db_session.commit()

    stock = InventorySnapshot(
        plant_id=plant.id, material_id=material.id, snapshot_date=date.today(), usable_physical_stock=500.0, uom="KG"
    )
    cons = ConsumptionHistory(
        plant_id=plant.id, material_id=material.id, consumption_date=date.today(), quantity=50.0, uom="KG"
    )
    db_session.add_all([stock, cons])
    db_session.commit()

    engine = PlanningReadinessEngine(db=db_session)
    report_ack = engine.acknowledge_warnings("PLANT-ACK", user_email="planner_readiness@example.com")

    assert report_ack.is_acknowledged is True
    assert report_ack.acknowledged_by == "planner_readiness@example.com"

    # Verify audit log recorded
    log = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "ACKNOWLEDGE_PLANNING_READINESS_WARNINGS")
        .first()
    )
    assert log is not None
    assert log.resource_id == "PLANT-ACK"


def test_blocked_acknowledgement_rejection(db_session: Session) -> None:
    plant = Plant(code="PLANT-FAIL-ACK", name="Fail Ack Plant")
    db_session.add(plant)
    db_session.commit()

    engine = PlanningReadinessEngine(db=db_session)
    with pytest.raises(Exception) as exc_info:
        engine.acknowledge_warnings("PLANT-FAIL-ACK")
    assert "CANNOT_ACKNOWLEDGE_BLOCKED_STATE" in str(exc_info.value) or "blocking issues exist" in str(exc_info.value)


def test_planning_readiness_api_endpoints(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = _seed_planner(db_session)

    plant = Plant(code="PLANT-API-R", name="API Readiness Plant")
    material = Material(code="MAT-API-R", description="Mat API", base_uom="KG")
    db_session.add_all([plant, material])
    db_session.commit()

    stock = InventorySnapshot(
        plant_id=plant.id, material_id=material.id, snapshot_date=date.today(), usable_physical_stock=100.0, uom="KG"
    )
    cons = ConsumptionHistory(
        plant_id=plant.id, material_id=material.id, consumption_date=date.today(), quantity=10.0, uom="KG"
    )
    db_session.add_all([stock, cons])
    db_session.commit()

    # 1. GET /api/v1/planning/readiness
    res_get = client.get("/api/v1/planning/readiness?plant_code=PLANT-API-R", headers=headers)
    assert res_get.status_code == 200
    data_get = res_get.json()
    assert data_get["plant_code"] == "PLANT-API-R"
    assert data_get["can_proceed_to_planning"] is True

    # 2. POST /api/v1/planning/readiness/acknowledge
    res_ack = client.post(
        "/api/v1/planning/readiness/acknowledge",
        json={"plant_code": "PLANT-API-R"},
        headers=headers,
    )
    assert res_ack.status_code == 200
    data_ack = res_ack.json()
    assert data_ack["is_acknowledged"] is True

    # 3. GET /api/v1/planning/readiness/history
    res_hist = client.get("/api/v1/planning/readiness/history?plant_code=PLANT-API-R", headers=headers)
    assert res_hist.status_code == 200
    data_hist = res_hist.json()
    assert len(data_hist) >= 1
