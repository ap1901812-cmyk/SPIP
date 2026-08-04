from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.db.models.domain import ConsumptionHistory, InventorySnapshot, Material, PlanningExecutionRecord, Plant
from app.db.models.user import RoleEnum, User, UserRole
from app.services.planning.orchestrator import (
    execute_full_planning_pipeline,
    get_planning_execution_details,
    get_planning_execution_history,
)


def _seed_planner(db: Session) -> dict[str, str]:
    user = User(
        email="planner_p8@example.com",
        full_name="Phase8 Planner",
        hashed_password=hash_password("Pass123!"),
        is_active=True,
    )
    user.roles.append(UserRole(role_name=RoleEnum.PLANNER.value))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user_id=user.id, email=user.email, roles=[RoleEnum.PLANNER.value])
    return {"Authorization": f"Bearer {token}"}


def test_orchestrator_pipeline_execution(db_session: Session) -> None:
    plant = Plant(code="P-ORCH-1", name="Orchestrator Plant")
    mat = Material(code="RM-ORCH-1", description="RM Orchestrator", material_type="RM", base_uom="KG")
    db_session.add_all([plant, mat])
    db_session.commit()

    ch = ConsumptionHistory(
        plant_id=plant.id,
        material_id=mat.id,
        consumption_date=date(2026, 7, 20),
        quantity=100.0,
        uom="KG",
        source="SAP_MB51",
    )
    inv = InventorySnapshot(
        plant_id=plant.id,
        material_id=mat.id,
        snapshot_date=date(2026, 7, 20),
        usable_physical_stock=500.0,
        uom="KG",
        source="SAP_MB5B",
    )
    db_session.add_all([ch, inv])
    db_session.commit()

    res = execute_full_planning_pipeline(
        db=db_session,
        plant_code="P-ORCH-1",
        material_code="RM-ORCH-1",
        horizon_days=30,
    )

    assert res.plant_code == "P-ORCH-1"
    assert res.material_code == "RM-ORCH-1"
    assert res.execution_metadata.status == "SUCCESS"
    assert res.execution_metadata.duration_ms >= 0
    assert "ENTERPRISE_DATA_INTELLIGENCE" in res.execution_metadata.modules_executed
    assert "PLANNING_READINESS" in res.execution_metadata.modules_executed

    # Verify execution record saved in DB
    recs = get_planning_execution_history(db_session, plant_code="P-ORCH-1")
    assert len(recs) == 1
    assert recs[0]["execution_status"] == "SUCCESS"


def test_orchestrator_execution_details(db_session: Session) -> None:
    plant = Plant(code="P-ORCH-2", name="Orchestrator Plant 2")
    mat = Material(code="FG-ORCH-2", description="FG Orchestrator", material_type="FG", base_uom="EA")
    db_session.add_all([plant, mat])
    db_session.commit()

    ch = ConsumptionHistory(
        plant_id=plant.id,
        material_id=mat.id,
        consumption_date=date(2026, 7, 20),
        quantity=100.0,
        uom="EA",
        source="SAP_MB51",
    )
    inv = InventorySnapshot(
        plant_id=plant.id,
        material_id=mat.id,
        snapshot_date=date(2026, 7, 20),
        usable_physical_stock=500.0,
        uom="EA",
        source="SAP_MB5B",
    )
    db_session.add_all([ch, inv])
    db_session.commit()

    res = execute_full_planning_pipeline(
        db=db_session,
        plant_code="P-ORCH-2",
        material_code="FG-ORCH-2",
        horizon_days=30,
    )

    recs = get_planning_execution_history(db_session, plant_code="P-ORCH-2")
    exec_id = recs[0]["id"]

    details = get_planning_execution_details(db_session, execution_id=exec_id)
    assert details is not None
    assert details["plant_code"] == "P-ORCH-2"
    assert details["material_code"] == "FG-ORCH-2"
    assert len(details["modules_executed"]) > 0


def test_orchestrator_api_endpoints(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = _seed_planner(db_session)

    plant = Plant(code="P-P8-API", name="P8 API Plant")
    mat = Material(code="M-P8-API", description="P8 Material API", material_type="RM", base_uom="KG")
    db_session.add_all([plant, mat])
    db_session.commit()

    ch = ConsumptionHistory(
        plant_id=plant.id,
        material_id=mat.id,
        consumption_date=date(2026, 7, 20),
        quantity=100.0,
        uom="KG",
        source="SAP_MB51",
    )
    inv = InventorySnapshot(
        plant_id=plant.id,
        material_id=mat.id,
        snapshot_date=date(2026, 7, 20),
        usable_physical_stock=500.0,
        uom="KG",
        source="SAP_MB5B",
    )
    db_session.add_all([ch, inv])
    db_session.commit()

    # 1. POST /api/v1/planning/execute
    res_exec = client.post(
        "/api/v1/planning/execute",
        json={"plant_code": "P-P8-API", "material_code": "M-P8-API", "horizon_days": 14},
        headers=headers,
    )
    assert res_exec.status_code == 200
    data_exec = res_exec.json()
    assert data_exec["plant_code"] == "P-P8-API"
    assert data_exec["execution_metadata"]["status"] == "SUCCESS"

    # 2. GET /api/v1/planning/executions
    res_hist = client.get("/api/v1/planning/executions?plant_code=P-P8-API", headers=headers)
    assert res_hist.status_code == 200
    data_hist = res_hist.json()
    assert len(data_hist) >= 1
    exec_id = data_hist[0]["id"]

    # 3. GET /api/v1/planning/executions/{execution_id}
    res_det = client.get(f"/api/v1/planning/executions/{exec_id}", headers=headers)
    assert res_det.status_code == 200
    data_det = res_det.json()
    assert data_det["id"] == exec_id
    assert data_det["plant_code"] == "P-P8-API"
