from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.db.models.domain import (
    ConsumptionHistory,
    InventorySnapshot,
    Material,
    Plant,
    PlantMaterial,
    Vendor,
    VendorMaterial,
)
from app.db.models.user import RoleEnum, User, UserRole
from app.services.planning.allocation_engine import (
    approve_procurement_allocation,
    generate_procurement_allocations,
)
from app.services.planning.decision_support import get_decision_support_summary
from app.services.planning.explainability import get_explainability_report
from app.services.planning.orchestrator import execute_full_planning_pipeline
from app.services.planning.procurement import generate_procurement_recommendations
from app.services.reporting import VALID_REPORT_TYPES, get_report_dataset


def _seed_user(db: Session, roles: list[str]) -> dict[str, str]:
    user = User(
        email=f"user_{roles[0].lower()}@spip.local",
        full_name="Phase12 User",
        hashed_password=hash_password("Pass123!"),
        is_active=True,
    )
    for r in roles:
        user.roles.append(UserRole(role_name=r))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user_id=user.id, email=user.email, roles=roles)
    return {"Authorization": f"Bearer {token}"}


def _seed_full_pipeline_data(db: Session, plant_code: str, mat_code: str) -> tuple[Plant, Material]:
    plant = Plant(code=plant_code, name=f"Plant {plant_code}")
    mat = Material(
        code=mat_code,
        description=f"Polymer RM {mat_code}",
        material_type="RM",
        material_group="POLYMERS",
        storage_capacity_limit=5000.0,
        base_uom="KG",
    )
    vendor = Vendor(code=f"VEND-{plant_code}", name="Supplier Corp", capacity_per_day=500.0)
    db.add_all([plant, mat, vendor])
    db.commit()

    pm = PlantMaterial(
        plant_id=plant.id,
        material_id=mat.id,
        abc_class="A",
        service_level_z=2.05,
        review_period_days=7,
        lead_time_1=10.0,
        lead_time_2=3.0,
        safety_stock_1=200.0,
        safety_stock_2=100.0,
    )
    vm = VendorMaterial(
        vendor_id=vendor.id,
        material_id=mat.id,
        is_primary=True,
        min_order_qty=100.0,
    )
    for i in range(1, 15):
        ch = ConsumptionHistory(
            plant_id=plant.id,
            material_id=mat.id,
            consumption_date=date.today() - timedelta(days=i),
            quantity=50.0,
            uom="KG",
            source="SAP_MB51",
        )
        db.add(ch)

    inv = InventorySnapshot(
        plant_id=plant.id,
        material_id=mat.id,
        snapshot_date=date.today(),
        usable_physical_stock=300.0,
        uom="KG",
        source="SAP_MB5B",
    )
    db.add_all([pm, vm, inv])
    db.commit()
    return plant, mat


def test_report_exports_all_types(client: TestClient, db_session: Session) -> None:
    headers = _seed_user(db_session, [RoleEnum.PLANNER.value])

    for r_type in VALID_REPORT_TYPES:
        for fmt in ["csv", "xlsx", "pdf"]:
            res = client.get(
                f"/api/v1/reports/export?report_type={r_type}&format={fmt}",
                headers=headers,
            )
            assert res.status_code == 200, f"Report {r_type} export format {fmt} failed"
            assert len(res.content) > 0


def test_planning_executions_telemetry(client: TestClient, db_session: Session) -> None:
    headers = _seed_user(db_session, [RoleEnum.PLANNER.value])
    _seed_full_pipeline_data(db_session, "P-P12-TEL", "RM-P12-TEL")

    res = client.get("/api/v1/planning/executions/telemetry?plant_code=P-P12-TEL", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_executions" in data
    assert "success_rate_percentage" in data
    assert "average_duration_ms" in data


def test_end_to_end_planning_pipeline_integration(db_session: Session) -> None:
    plant, mat = _seed_full_pipeline_data(db_session, "P-P12-E2E", "RM-P12-E2E")

    # Step 1: Central Planning Orchestrator
    orchestrator_res = execute_full_planning_pipeline(
        db=db_session, plant_code="P-P12-E2E", material_code="RM-P12-E2E"
    )
    assert orchestrator_res.execution_metadata.status == "SUCCESS"

    # Step 2: Procurement Recommendations (Phase 9)
    recs_summary = generate_procurement_recommendations(
        db=db_session, plant_code="P-P12-E2E", material_code="RM-P12-E2E"
    )
    assert recs_summary.total_recommendations_generated >= 1

    # Step 3: Dynamic Vendor Allocations (Phase 10)
    allocs_summary = generate_procurement_allocations(
        db=db_session, plant_code="P-P12-E2E"
    )
    assert allocs_summary.total_allocations_generated >= 1

    # Step 4: Planner Approval Workflow (Phase 10)
    alloc_id = allocs_summary.allocations[0].id
    approved_alloc = approve_procurement_allocation(db=db_session, allocation_id=alloc_id)
    assert approved_alloc.status == "APPROVED"
    assert approved_alloc.notification_payload is not None

    # Step 5: Decision Support & Explainability (Phase 11)
    ds_summary = get_decision_support_summary(db=db_session, plant_code="P-P12-E2E")
    assert ds_summary.plant_code == "P-P12-E2E"

    exp_report = get_explainability_report(db=db_session, plant_code="P-P12-E2E", material_code="RM-P12-E2E")
    assert exp_report.material_code == "RM-P12-E2E"
