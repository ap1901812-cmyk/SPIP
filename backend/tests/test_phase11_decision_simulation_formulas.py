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
    SimulationRun,
    Vendor,
    VendorMaterial,
)
from app.db.models.user import RoleEnum, User, UserRole
from app.services.admin.formula_explorer import AdminFormulaExplorerRegistry
from app.services.planning.decision_support import get_decision_support_summary
from app.services.planning.explainability import get_explainability_report
from app.services.planning.simulation import (
    ScenarioOverrides,
    get_simulation_detail,
    get_simulation_history,
    run_what_if_simulation,
)


def _seed_users(db: Session) -> tuple[dict[str, str], dict[str, str]]:
    admin = User(
        email="admin_p11@spip.local",
        full_name="Phase11 Admin",
        hashed_password=hash_password("Pass123!"),
        is_active=True,
    )
    admin.roles.append(UserRole(role_name=RoleEnum.ADMIN.value))

    planner = User(
        email="planner_p11@spip.local",
        full_name="Phase11 Planner",
        hashed_password=hash_password("Pass123!"),
        is_active=True,
    )
    planner.roles.append(UserRole(role_name=RoleEnum.PLANNER.value))

    db.add_all([admin, planner])
    db.commit()
    db.refresh(admin)
    db.refresh(planner)

    admin_token = create_access_token(user_id=admin.id, email=admin.email, roles=[RoleEnum.ADMIN.value])
    planner_token = create_access_token(user_id=planner.id, email=planner.email, roles=[RoleEnum.PLANNER.value])

    return {"Authorization": f"Bearer {admin_token}"}, {"Authorization": f"Bearer {planner_token}"}


def _seed_phase11_data(db: Session, plant_code: str, mat_code: str) -> tuple[Plant, Material]:
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

    rec = ProcurementRecommendation(
        plant_id=plant.id,
        material_id=mat.id,
        recommended_qty=400.0,
        recommended_vendor_id=vendor.id,
        recommended_procurement_date=date.today(),
        dispatch_date=date.today() + timedelta(days=2),
        expected_arrival_date=date.today() + timedelta(days=12),
        priority="HIGH",
        planning_mode="PROACTIVE",
        status="RECOMMENDED",
        reason="Test recommendation",
    )
    db.add(rec)
    db.commit()

    return plant, mat


def test_decision_support_summary(db_session: Session) -> None:
    plant, mat = _seed_phase11_data(db_session, "P-P11-DS", "RM-P11-DS")

    summary = get_decision_support_summary(db_session, plant_code="P-P11-DS", material_code="RM-P11-DS")

    assert summary.plant_code == "P-P11-DS"
    assert summary.planning_summary["as_of_timestamp"] != ""
    assert summary.procurement_summary["total_recommendations_count"] >= 1
    assert summary.inventory_summary["usable_physical_stock"] == 300.0
    assert summary.inventory_summary["average_daily_demand"] == 50.0
    assert len(summary.recommendation_summary) >= 1


def test_explainability_report(db_session: Session) -> None:
    plant, mat = _seed_phase11_data(db_session, "P-P11-EXP", "RM-P11-EXP")

    report = get_explainability_report(db_session, plant_code="P-P11-EXP", material_code="RM-P11-EXP")

    assert report.plant_code == "P-P11-EXP"
    assert report.material_code == "RM-P11-EXP"
    assert len(report.source_data_used) >= 1
    assert len(report.planning_modules_involved) >= 1
    assert len(report.business_rules_applied) >= 1
    assert report.intermediate_calculations["average_daily_demand"] == 50.0
    assert "readiness_score" in report.confidence_indicators


def test_what_if_simulation_engine_zero_side_effects(db_session: Session) -> None:
    plant, mat = _seed_phase11_data(db_session, "P-P11-SIM", "RM-P11-SIM")
    initial_stock = 300.0

    # Execute simulation with +50% demand surge
    sim_res = run_what_if_simulation(
        db=db_session,
        user_id=1,
        scenario_name="Demand Surge +50%",
        plant_code="P-P11-SIM",
        material_code="RM-P11-SIM",
        overrides=ScenarioOverrides(demand_multiplier=1.5),
    )

    assert sim_res.scenario_name == "Demand Surge +50%"
    assert sim_res.results["simulation_impact_summary"]["simulated_daily_demand"] == 75.0

    # Verify Production Data in Database was NEVER mutated
    inv_db = (
        db_session.query(InventorySnapshot)
        .filter(InventorySnapshot.plant_id == plant.id, InventorySnapshot.material_id == mat.id)
        .first()
    )
    assert inv_db.usable_physical_stock == initial_stock

    # Verify simulation record saved
    history = get_simulation_history(db_session, user_id=1)
    assert len(history) >= 1

    detail = get_simulation_detail(db_session, simulation_id=sim_res.id)
    assert detail["scenario_name"] == "Demand Surge +50%"


def test_admin_formula_explorer_catalog_and_rbac(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_headers, planner_headers = _seed_users(db_session)

    # 1. Admin accesses Formula Explorer Catalog -> 200 OK
    res_admin = client.get("/api/v1/admin/formulas", headers=admin_headers)
    assert res_admin.status_code == 200
    catalog = res_admin.json()
    assert len(catalog) >= 10
    module_names = {entry["source_module"] for entry in catalog}
    assert "Enterprise Data Intelligence" in module_names
    assert "Planning Readiness" in module_names
    assert "RMPM Statistical Planning" in module_names
    assert "Forecasting Engine" in module_names
    assert "Dynamic Procurement Allocation Engine" in module_names

    # 2. Get specific formula detail
    res_detail = client.get("/api/v1/admin/formulas/RMPM-01", headers=admin_headers)
    assert res_detail.status_code == 200
    assert res_detail.json()["id"] == "RMPM-01"
    assert "SS_1" in res_detail.json()["mathematical_formula"]

    # 3. Planner accesses Formula Explorer -> 403 Forbidden
    res_planner = client.get("/api/v1/admin/formulas", headers=planner_headers)
    assert res_planner.status_code == 403
