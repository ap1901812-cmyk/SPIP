from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.db.models.user import RoleEnum, User, UserRole
from app.services.planning.fg_engine import (
    compute_component_shortages,
    compute_fg_impact,
    compute_procurement_recommendations,
    explode_fg_demands,
)
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


def test_stateless_fg_engine_pure_functions() -> None:
    # 1. Test explode_fg_demands
    demand_items = [
        {"fg_material_id": 1, "fg_code": "FG-1001", "plant_code": "PLANT-1000", "demand_quantity": 100.0}
    ]
    bom_map = {
        1: [
            {"fg_material_id": 1, "component_material_id": 10, "required_quantity": 2.0, "unit_of_measure": "KG"},
            {"fg_material_id": 1, "component_material_id": 20, "required_quantity": 1.0, "unit_of_measure": "ROLL"},
        ]
    }

    gross_reqs, usages = explode_fg_demands(demand_items, bom_map)
    assert gross_reqs[("PLANT-1000", 10)] == 200.0
    assert gross_reqs[("PLANT-1000", 20)] == 100.0

    # 2. Test compute_component_shortages
    material_info_map = {
        10: {"id": 10, "code": "RM-10", "description": "Resin A", "material_type": "RM", "base_uom": "KG"},
        20: {"id": 20, "code": "PM-20", "description": "Film B", "material_type": "PM", "base_uom": "ROLL"},
    }
    availability_map = {
        ("PLANT-1000", 10): {"usable_physical_stock": 50.0, "planning_availability": 50.0},
        ("PLANT-1000", 20): {"usable_physical_stock": 150.0, "planning_availability": 150.0},
    }

    shortages = compute_component_shortages(gross_reqs, material_info_map, availability_map)
    assert len(shortages) == 2

    shortage_10 = next(s for s in shortages if s["component_material_id"] == 10)
    assert shortage_10["shortage_quantity"] == 150.0
    assert shortage_10["criticality_status"] == "CRITICAL"
    assert "net shortage of 150.0 KG" in shortage_10["explanation"]

    # 3. Test compute_procurement_recommendations
    vendor_map = {
        10: {
            "vendor_code": "VEND-5001",
            "vendor_name": "Global Polymers",
            "vendor_lead_time_days": 10.0,
            "min_order_qty": 200.0,
        }
    }
    recs = compute_procurement_recommendations(shortages, vendor_map)
    assert len(recs) == 1
    rec = recs[0]
    assert rec["recommended_order_qty"] == 200.0  # adjusted up from 150.0 to MOQ 200.0
    assert "Minimum Order Qty of 200.0 KG" in rec["explanation"]

    # 4. Test compute_fg_impact
    fg_info_map = {1: {"id": 1, "code": "FG-1001", "description": "Container A"}}
    shortage_qty_map = {("PLANT-1000", 10): 150.0}
    avail_qty_map = {("PLANT-1000", 10): 50.0, ("PLANT-1000", 20): 150.0}

    impacts = compute_fg_impact(demand_items, fg_info_map, bom_map, shortage_qty_map, avail_qty_map)
    assert len(impacts) == 1
    imp = impacts[0]
    assert imp["feasible_production"] == 25.0  # 50 available / 2.0 per unit = 25 units
    assert imp["unmet_demand"] == 75.0
    assert imp["bottleneck_component_code"] == "MAT-10"
    assert imp["risk_status"] == "AT_RISK"
    assert "limits feasible production to 25.0 units" in imp["explanation"]


def test_planning_run_api_custom_demand(client: TestClient, db_session: Session) -> None:
    token = _seed_user(db_session, "planner_run1@spip.local", RoleEnum.PLANNER.value)
    MockSAPAdapter().sync_to_database(db_session)

    request_payload = {
        "demands": [
            {"fg_code": "FG-1001", "plant_code": "PLANT-1000", "demand_quantity": 100.0}
        ]
    }

    res = client.post("/api/v1/planning/run", json=request_payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert "summary" in data
    assert "component_requirements" in data
    assert "procurement_recommendations" in data
    assert "affected_finished_goods" in data
    assert data["summary"]["total_demand_items_evaluated"] == 1


def test_planning_shortages_and_recommendations_apis(client: TestClient, db_session: Session) -> None:
    token = _seed_user(db_session, "planner_run2@spip.local", RoleEnum.PLANNER.value)
    MockSAPAdapter().sync_to_database(db_session)

    res_shortages = client.get("/api/v1/planning/shortages?plant_code=PLANT-1000", headers={"Authorization": f"Bearer {token}"})
    assert res_shortages.status_code == 200
    s_data = res_shortages.json()
    assert "total_shortages_count" in s_data
    assert "shortages" in s_data

    res_recs = client.get("/api/v1/planning/recommendations?plant_code=PLANT-1000", headers={"Authorization": f"Bearer {token}"})
    assert res_recs.status_code == 200
    r_data = res_recs.json()
    assert "total_recommendations_count" in r_data
    assert "recommendations" in r_data
