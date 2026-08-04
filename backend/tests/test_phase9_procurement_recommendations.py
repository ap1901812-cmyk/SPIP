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
    ProcurementRecommendation,
    Vendor,
    VendorMaterial,
)
from app.db.models.user import RoleEnum, User, UserRole
from app.services.planning.procurement import (
    generate_procurement_recommendations,
    get_procurement_recommendation_by_id,
    get_procurement_recommendation_history,
    refresh_procurement_recommendations,
)


def _seed_planner(db: Session) -> dict[str, str]:
    user = User(
        email="planner_p9@spip.local",
        full_name="Phase9 Planner",
        hashed_password=hash_password("Pass123!"),
        is_active=True,
    )
    user.roles.append(UserRole(role_name=RoleEnum.PLANNER.value))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user_id=user.id, email=user.email, roles=[RoleEnum.PLANNER.value])
    return {"Authorization": f"Bearer {token}"}


def _seed_procurement_data(db: Session, plant_code: str, mat_code: str, usable_stock: float = 350.0) -> tuple[Plant, Material]:
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
        plant_id=plant.id,
        is_primary=True,
        vendor_lead_time_days=10.0,
        min_order_qty=100.0,
    )
    # Add multiple consumption records relative to today to guarantee daily requirement > 0
    for day_offset in range(1, 15):
        ch = ConsumptionHistory(
            plant_id=plant.id,
            material_id=mat.id,
            consumption_date=date.today() - timedelta(days=day_offset),
            quantity=50.0,
            uom="KG",
            source="SAP_MB51",
        )
        db.add(ch)

    inv = InventorySnapshot(
        plant_id=plant.id,
        material_id=mat.id,
        snapshot_date=date(2026, 7, 20),
        usable_physical_stock=usable_stock,
        uom="KG",
        source="SAP_MB5B",
    )
    db.add_all([pm, vm, inv])
    db.commit()
    return plant, mat


def test_proactive_procurement_recommendation_generation(db_session: Session) -> None:
    plant, mat = _seed_procurement_data(db_session, "P-P9-PRO", "RM-P9-PRO", usable_stock=350.0)

    summary = generate_procurement_recommendations(
        db=db_session,
        plant_code="P-P9-PRO",
        material_code="RM-P9-PRO",
        horizon_days=15,
        planning_mode="PROACTIVE",
    )

    assert summary.plant_code == "P-P9-PRO"
    assert summary.total_recommendations_generated == 1
    assert summary.proactive_count == 1

    rec = summary.recommendations[0]
    assert rec.material_code == "RM-P9-PRO"
    assert rec.material_type == "RM"
    assert rec.recommended_qty > 0.0
    assert rec.planning_mode == "PROACTIVE"
    assert rec.priority in ("HIGH", "MEDIUM")
    assert rec.recommended_procurement_date <= rec.expected_arrival_date
    assert rec.explanation.requirement_reason != ""
    assert rec.explanation.applied_constraints["lead_time_days"] == 10.0


def test_reactive_procurement_recommendation_generation(db_session: Session) -> None:
    plant, mat = _seed_procurement_data(db_session, "P-P9-REA", "RM-P9-REA", usable_stock=0.0)

    summary = generate_procurement_recommendations(
        db=db_session,
        plant_code="P-P9-REA",
        material_code="RM-P9-REA",
        horizon_days=15,
        planning_mode="REACTIVE",
    )

    assert summary.plant_code == "P-P9-REA"
    assert summary.total_recommendations_generated == 1
    assert summary.reactive_count == 1

    rec = summary.recommendations[0]
    assert rec.priority == "CRITICAL"
    assert rec.planning_mode == "REACTIVE"
    assert rec.explanation.triggering_module != ""


def test_dynamic_recommendation_refresh(db_session: Session) -> None:
    plant, mat = _seed_procurement_data(db_session, "P-P9-REF", "RM-P9-REF", usable_stock=250.0)

    summary = refresh_procurement_recommendations(db=db_session, plant_code="P-P9-REF")
    assert summary.plant_code == "P-P9-REF"
    assert summary.total_recommendations_generated >= 1

    history = get_procurement_recommendation_history(db_session, plant_code="P-P9-REF")
    assert len(history) >= 1
    assert history[0]["material_code"] == "RM-P9-REF"

    detail = get_procurement_recommendation_by_id(db_session, recommendation_id=history[0]["id"])
    assert detail["id"] == history[0]["id"]
    assert detail["explanation"] is not None


def test_procurement_recommendation_api_endpoints(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = _seed_planner(db_session)
    _seed_procurement_data(db_session, "P-P9-API", "RM-P9-API", usable_stock=200.0)

    # 1. POST /api/v1/planning/procurement-recommendations/generate
    res_gen = client.post(
        "/api/v1/planning/procurement-recommendations/generate",
        json={
            "plant_code": "P-P9-API",
            "material_code": "RM-P9-API",
            "horizon_days": 15,
            "planning_mode": "PROACTIVE",
        },
        headers=headers,
    )
    assert res_gen.status_code == 200
    data_gen = res_gen.json()
    assert data_gen["plant_code"] == "P-P9-API"
    assert data_gen["total_recommendations_generated"] >= 1

    # 2. POST /api/v1/planning/procurement-recommendations/refresh
    res_ref = client.post(
        "/api/v1/planning/procurement-recommendations/refresh",
        json={"plant_code": "P-P9-API"},
        headers=headers,
    )
    assert res_ref.status_code == 200

    # 3. GET /api/v1/planning/procurement-recommendations
    res_list = client.get(
        "/api/v1/planning/procurement-recommendations?plant_code=P-P9-API", headers=headers
    )
    assert res_list.status_code == 200
    data_list = res_list.json()
    assert len(data_list) >= 1
    rec_id = data_list[0]["id"]

    # 4. GET /api/v1/planning/procurement-recommendations/{recommendation_id}
    res_det = client.get(
        f"/api/v1/planning/procurement-recommendations/{rec_id}", headers=headers
    )
    assert res_det.status_code == 200
    data_det = res_det.json()
    assert data_det["id"] == rec_id
    assert data_det["material_code"] == "RM-P9-API"
    assert "explanation" in data_det
