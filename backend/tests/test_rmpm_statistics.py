from __future__ import annotations

from datetime import date

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
    PurchaseOrder,
    PurchaseOrderLine,
    Vendor,
    VendorMaterial,
)
from app.db.models.user import RoleEnum, User, UserRole
from app.services.planning.consumption_intelligence import analyze_consumption_intelligence
from app.services.planning.engine import evaluate_material_planning
from app.services.planning.inventory_intelligence import analyze_inventory_intelligence
from app.services.planning.lead_time import resolve_dual_lead_time
from app.services.planning.safety_stock import calculate_dual_safety_stock


def _seed_planner(db: Session) -> dict[str, str]:
    user = User(
        email="planner_rmpm@example.com",
        full_name="RMPM Planner",
        hashed_password=hash_password("Pass123!"),
        is_active=True,
    )
    user.roles.append(UserRole(role_name=RoleEnum.PLANNER.value))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user_id=user.id, email=user.email, roles=[RoleEnum.PLANNER.value])
    return {"Authorization": f"Bearer {token}"}


def test_consumption_intelligence_engine(db_session: Session) -> None:
    plant = Plant(code="P-CI-1", name="Consumption Plant")
    mat = Material(code="M-CI-1", description="Mat CI", base_uom="KG")
    db_session.add_all([plant, mat])
    db_session.commit()

    # Add 10 days of consumption
    today = date.today()
    for i in range(10):
        c = ConsumptionHistory(
            plant_id=plant.id,
            material_id=mat.id,
            consumption_date=today - date.resolution * i,  # daily step
            quantity=100.0 if i < 5 else 50.0,
            uom="KG",
        )
        db_session.add(c)
    db_session.commit()

    result = analyze_consumption_intelligence(db_session, plant.id, mat.id, window_days=30)
    assert result.average_daily_demand == 75.0
    assert result.demand_std_dev == 25.0
    assert result.observation_days_count == 10
    assert result.consumption_variability == 0.3333


def test_inventory_intelligence_engine(db_session: Session) -> None:
    plant = Plant(code="P-II-1", name="Inventory Plant")
    mat = Material(code="M-II-1", description="Mat II", base_uom="KG")
    db_session.add_all([plant, mat])
    db_session.commit()

    stock = InventorySnapshot(
        plant_id=plant.id,
        material_id=mat.id,
        snapshot_date=date.today(),
        usable_physical_stock=300.0,
        uom="KG",
    )
    db_session.add(stock)

    vendor = Vendor(code="V-II-1", name="Vendor II")
    db_session.add(vendor)
    db_session.commit()

    po = PurchaseOrder(
        po_number="PO-II-1", plant_id=plant.id, vendor_id=vendor.id, status="OPEN", po_date=date.today()
    )
    db_session.add(po)
    db_session.commit()

    po_line = PurchaseOrderLine(
        po_id=po.id,
        line_number=1,
        material_id=mat.id,
        order_quantity=200.0,
        open_quantity=200.0,
        uom="KG",
        expected_delivery_date=date.today(),
        status="CONFIRMED",
    )
    db_session.add(po_line)
    db_session.commit()

    result = analyze_inventory_intelligence(
        db_session, plant.id, mat.id, average_daily_demand=50.0
    )
    assert result.usable_physical_stock == 300.0
    assert result.incoming_inventory == 200.0
    assert result.planning_available_inventory == 500.0
    assert result.days_of_inventory == 10.0  # 500 / 50.0


def test_dual_lead_time_and_safety_stock(db_session: Session) -> None:
    plant = Plant(code="P-LT-1", name="LT Plant")
    mat = Material(code="M-LT-1", description="Mat LT", base_uom="KG")
    db_session.add_all([plant, mat])
    db_session.commit()

    pm = PlantMaterial(plant_id=plant.id, material_id=mat.id, lead_time_1=10.0, lead_time_2=4.0)
    db_session.add(pm)
    db_session.commit()

    lt_res = resolve_dual_lead_time(db_session, plant.id, mat.id, plant_material=pm)
    assert lt_res.lead_time_1 == 10.0
    assert lt_res.lead_time_2 == 4.0

    ss_res = calculate_dual_safety_stock(
        demand_std_dev=10.0,
        lead_time_1=lt_res.lead_time_1,
        lead_time_2=lt_res.lead_time_2,
        plant_material=pm,
    )
    assert ss_res.safety_stock_1 > ss_res.safety_stock_2


def test_rmpm_statistical_planning_engine_material_status(db_session: Session) -> None:
    plant = Plant(code="P-RMPM-1", name="RMPM Plant")
    mat = Material(code="M-RMPM-1", description="Mat RMPM", base_uom="KG")
    db_session.add_all([plant, mat])
    db_session.commit()

    pm = PlantMaterial(
        plant_id=plant.id,
        material_id=mat.id,
        lead_time_1=10.0,
        lead_time_2=4.0,
        service_level_z=1.65,
    )
    db_session.add(pm)

    stock = InventorySnapshot(
        plant_id=plant.id, material_id=mat.id, snapshot_date=date.today(), usable_physical_stock=1000.0, uom="KG"
    )
    cons = ConsumptionHistory(
        plant_id=plant.id, material_id=mat.id, consumption_date=date.today(), quantity=50.0, uom="KG"
    )
    db_session.add_all([stock, cons])
    db_session.commit()

    result = evaluate_material_planning(db_session, "P-RMPM-1", "M-RMPM-1")

    assert result.plant_code == "P-RMPM-1"
    assert result.material_code == "M-RMPM-1"
    assert result.lead_time_1 == 10.0
    assert result.lead_time_2 == 4.0
    assert result.trigger_1 > result.trigger_2
    assert result.rmpm_material_status in ["CRITICAL", "REORDER_REQUIRED", "LOW_STOCK", "HEALTHY"]
    assert result.reorder_point == result.trigger_1  # Backwards compatibility check


def test_rmpm_planning_api_endpoints(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = _seed_planner(db_session)

    plant = Plant(code="P-API-RMPM", name="API RMPM Plant")
    mat = Material(code="M-API-RMPM", description="Mat API RMPM", base_uom="KG")
    db_session.add_all([plant, mat])
    db_session.commit()

    pm = PlantMaterial(plant_id=plant.id, material_id=mat.id, lead_time_1=8.0, lead_time_2=3.0)
    stock = InventorySnapshot(
        plant_id=plant.id, material_id=mat.id, snapshot_date=date.today(), usable_physical_stock=200.0, uom="KG"
    )
    cons = ConsumptionHistory(
        plant_id=plant.id, material_id=mat.id, consumption_date=date.today(), quantity=20.0, uom="KG"
    )
    db_session.add_all([pm, stock, cons])
    db_session.commit()

    res = client.get("/api/v1/planning/materials/M-API-RMPM?plant_code=P-API-RMPM", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["material_code"] == "M-API-RMPM"
    assert "lead_time_1" in data
    assert "lead_time_2" in data
    assert "trigger_1" in data
    assert "trigger_2" in data
    assert "days_of_inventory" in data
    assert "rmpm_material_status" in data
