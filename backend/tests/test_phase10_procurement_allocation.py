from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.db.models.domain import (
    Allocation,
    ConsumptionHistory,
    InventorySnapshot,
    Material,
    Plant,
    PlantMaterial,
    ProcurementRecommendation,
    Vendor,
    VendorMaterial,
)
from app.db.models.user import RoleEnum, User, UserRole
from app.services.planning.allocation_engine import (
    approve_procurement_allocation,
    edit_procurement_allocation,
    generate_procurement_allocations,
    get_procurement_allocation_detail,
    get_procurement_allocation_history,
    preview_notification_payload,
)


def _seed_planner(db: Session) -> dict[str, str]:
    user = User(
        email="planner_p10@spip.local",
        full_name="Phase10 Planner",
        hashed_password=hash_password("Pass123!"),
        is_active=True,
    )
    user.roles.append(UserRole(role_name=RoleEnum.PLANNER.value))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user_id=user.id, email=user.email, roles=[RoleEnum.PLANNER.value])
    return {"Authorization": f"Bearer {token}"}


def _seed_allocation_data(db: Session, plant_code: str, mat_code: str) -> tuple[Plant, Material, ProcurementRecommendation]:
    plant = Plant(code=plant_code, name=f"Plant {plant_code}")
    mat = Material(
        code=mat_code,
        description=f"Polymer RM {mat_code}",
        material_type="RM",
        material_group="POLYMERS",
        storage_capacity_limit=5000.0,
        base_uom="KG",
    )
    v1 = Vendor(code=f"VEND1-{plant_code}", name="Primary Supplier Ltd", capacity_per_day=300.0, contact_email="primary@vendor.com")
    v2 = Vendor(code=f"VEND2-{plant_code}", name="Secondary Supplier Ltd", capacity_per_day=500.0, contact_email="secondary@vendor.com")
    db.add_all([plant, mat, v1, v2])
    db.commit()

    vm1 = VendorMaterial(
        vendor_id=v1.id,
        material_id=mat.id,
        is_primary=True,
        min_order_qty=100.0,
    )
    vm2 = VendorMaterial(
        vendor_id=v2.id,
        material_id=mat.id,
        is_primary=False,
        min_order_qty=50.0,
    )
    rec = ProcurementRecommendation(
        plant_id=plant.id,
        material_id=mat.id,
        recommended_qty=500.0,
        recommended_vendor_id=v1.id,
        recommended_procurement_date=date.today(),
        dispatch_date=date.today() + timedelta(days=2),
        expected_arrival_date=date.today() + timedelta(days=9),
        priority="HIGH",
        planning_mode="PROACTIVE",
        status="RECOMMENDED",
        reason="Stockout risk buffer target breach.",
    )
    db.add_all([vm1, vm2, rec])
    db.commit()
    db.refresh(rec)
    return plant, mat, rec


def test_generate_procurement_allocations_multi_vendor_split(db_session: Session) -> None:
    plant, mat, rec = _seed_allocation_data(db_session, "P-P10-SPLIT", "RM-P10-SPLIT")

    summary = generate_procurement_allocations(
        db=db_session, plant_code="P-P10-SPLIT", recommendation_ids=[rec.id]
    )

    assert summary.plant_code == "P-P10-SPLIT"
    assert summary.total_allocations_generated == 2
    assert summary.total_quantity_allocated == 500.0

    alloc1 = summary.allocations[0]
    alloc2 = summary.allocations[1]

    # Primary vendor capped at 300.0
    assert alloc1.allocated_quantity == 300.0
    assert alloc1.status == "DRAFT"

    # Secondary vendor assigned remaining 200.0
    assert alloc2.allocated_quantity == 200.0
    assert alloc2.status == "DRAFT"


def test_edit_procurement_allocation_planner_workflow(db_session: Session) -> None:
    plant, mat, rec = _seed_allocation_data(db_session, "P-P10-EDIT", "RM-P10-EDIT")
    summary = generate_procurement_allocations(db=db_session, plant_code="P-P10-EDIT")

    alloc_id = summary.allocations[0].id
    edited = edit_procurement_allocation(
        db=db_session,
        allocation_id=alloc_id,
        allocated_quantity=350.0,
        notes="Planner adjusted vendor quota.",
    )

    assert edited.id == alloc_id
    assert edited.allocated_quantity == 350.0
    assert edited.allocation_notes == "Planner adjusted vendor quota."
    assert edited.version == 2


def test_approve_procurement_allocation_workflow(db_session: Session) -> None:
    plant, mat, rec = _seed_allocation_data(db_session, "P-P10-APP", "RM-P10-APP")
    summary = generate_procurement_allocations(db=db_session, plant_code="P-P10-APP")

    alloc_id = summary.allocations[0].id
    approved = approve_procurement_allocation(db=db_session, allocation_id=alloc_id)

    assert approved.status == "APPROVED"
    assert approved.notification_payload is not None
    assert "email_payload" in approved.notification_payload
    assert "in_app_payload" in approved.notification_payload
    assert approved.notification_payload["email_payload"]["subject"] != ""

    # Check recommendation status updated to ACCEPTED
    db_session.refresh(rec)
    assert rec.status == "ACCEPTED"


def test_procurement_allocation_api_endpoints(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = _seed_planner(db_session)
    plant, mat, rec = _seed_allocation_data(db_session, "P-P10-API", "RM-P10-API")

    # 1. POST /api/v1/planning/procurement-allocations/generate
    res_gen = client.post(
        "/api/v1/planning/procurement-allocations/generate",
        json={"plant_code": "P-P10-API", "recommendation_ids": [rec.id]},
        headers=headers,
    )
    assert res_gen.status_code == 200
    data_gen = res_gen.json()
    assert data_gen["plant_code"] == "P-P10-API"
    assert data_gen["total_allocations_generated"] >= 1
    alloc_id = data_gen["allocations"][0]["id"]

    # 2. PUT /api/v1/planning/procurement-allocations/{allocation_id}
    res_edit = client.put(
        f"/api/v1/planning/procurement-allocations/{alloc_id}",
        json={"allocated_quantity": 280.0, "allocation_notes": "API test edit"},
        headers=headers,
    )
    assert res_edit.status_code == 200
    assert res_edit.json()["allocated_quantity"] == 280.0

    # 3. POST /api/v1/planning/procurement-allocations/{allocation_id}/approve
    res_app = client.post(
        f"/api/v1/planning/procurement-allocations/{alloc_id}/approve",
        headers=headers,
    )
    assert res_app.status_code == 200
    assert res_app.json()["status"] == "APPROVED"

    # 4. GET /api/v1/planning/procurement-allocations
    res_list = client.get(
        "/api/v1/planning/procurement-allocations?plant_code=P-P10-API", headers=headers
    )
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1

    # 5. GET /api/v1/planning/procurement-allocations/{allocation_id}
    res_det = client.get(f"/api/v1/planning/procurement-allocations/{alloc_id}", headers=headers)
    assert res_det.status_code == 200
    assert res_det.json()["id"] == alloc_id

    # 6. GET /api/v1/planning/procurement-allocations/{allocation_id}/notifications
    res_notif = client.get(
        f"/api/v1/planning/procurement-allocations/{alloc_id}/notifications", headers=headers
    )
    assert res_notif.status_code == 200
    assert "email_payload" in res_notif.json()
