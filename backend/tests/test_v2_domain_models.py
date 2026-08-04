from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.db.models.domain import (
    Allocation,
    Material,
    PMOverride,
    PlanningReadinessScore,
    Plant,
    PlantMaterial,
    ProcurementRecommendation,
    ProductionReadinessRecord,
    RMTotalityMapping,
    SimulationRun,
    Vendor,
)
from app.db.models.user import User


def test_material_and_vendor_v2_extensions(db_session: Session) -> None:
    material = Material(
        code="V2-RM-100",
        description="V2 Polymer Raw Material",
        material_type="RM",
        material_group="POLYMERS",
        storage_capacity_limit=5000.0,
        base_uom="KG",
    )
    vendor = Vendor(
        code="V2-VEND-01",
        name="V2 Supplier Corp",
        capacity_per_day=50.0,
        lead_time_1_days=14.0,
        lead_time_2_days=5.0,
    )
    db_session.add_all([material, vendor])
    db_session.commit()

    assert material.id is not None
    assert material.material_group == "POLYMERS"
    assert material.storage_capacity_limit == 5000.0

    assert vendor.id is not None
    assert vendor.capacity_per_day == 50.0
    assert vendor.lead_time_1_days == 14.0
    assert vendor.lead_time_2_days == 5.0


def test_plant_material_rmpm_dual_parameters(db_session: Session) -> None:
    plant = Plant(code="V2-PLANT-1", name="V2 Main Plant")
    material = Material(code="V2-MAT-1", description="V2 Material 1", base_uom="KG")
    db_session.add_all([plant, material])
    db_session.commit()

    pm = PlantMaterial(
        plant_id=plant.id,
        material_id=material.id,
        lead_time_1=15.0,
        lead_time_2=5.0,
        safety_stock_1=200.0,
        safety_stock_2=80.0,
        trigger_1=350.0,
        trigger_2=150.0,
    )
    db_session.add(pm)
    db_session.commit()

    assert pm.id is not None
    assert pm.lead_time_1 == 15.0
    assert pm.lead_time_2 == 5.0
    assert pm.safety_stock_1 == 200.0
    assert pm.safety_stock_2 == 80.0
    assert pm.trigger_1 == 350.0
    assert pm.trigger_2 == 150.0


def test_rm_totality_and_pm_override_models(db_session: Session) -> None:
    plant = Plant(code="V2-PLANT-2", name="V2 Secondary Plant")
    rm_mat = Material(code="RM-900", description="Raw Chemical A", material_type="RM", base_uom="KG")
    fg_mat = Material(code="FG-900", description="Finished Good Product 1", material_type="FG", base_uom="PCS")
    pm_mat = Material(code="PM-900", description="Outer Box", material_type="PM", base_uom="PCS")
    user = User(email="planner_v2@example.com", full_name="V2 Planner", hashed_password="hashed_pw")

    db_session.add_all([plant, rm_mat, fg_mat, pm_mat, user])
    db_session.commit()

    totality = RMTotalityMapping(
        plant_id=plant.id,
        rm_material_id=rm_mat.id,
        fg_group_name="CHEMICAL_EXPLOSIVES",
        consumption_ratio=1.2,
    )
    pm_override = PMOverride(
        plant_id=plant.id,
        fg_material_id=fg_mat.id,
        pm_material_id=pm_mat.id,
        override_ratio=1.05,
        notes="Planner adjusted for seasonal packaging loss",
        updated_by_user_id=user.id,
    )
    db_session.add_all([totality, pm_override])
    db_session.commit()

    assert totality.id is not None
    assert totality.fg_group_name == "CHEMICAL_EXPLOSIVES"
    assert totality.rm_material.code == "RM-900"

    assert pm_override.id is not None
    assert pm_override.override_ratio == 1.05
    assert pm_override.updated_by_user.email == "planner_v2@example.com"


def test_readiness_recommendation_readiness_models(db_session: Session) -> None:
    plant = Plant(code="V2-PLANT-3", name="V2 Third Plant")
    material = Material(code="MAT-V2-3", description="Test Mat", base_uom="KG")
    vendor = Vendor(code="VEND-V2-3", name="Vendor 3")
    user = User(email="test_user_sim@example.com", full_name="Sim User", hashed_password="pw")
    db_session.add_all([plant, material, vendor, user])
    db_session.commit()

    readiness = PlanningReadinessScore(
        plant_id=plant.id,
        score=92.5,
        missing_masters_count=0,
        missing_parameters_count=3,
        details_json='{"missing":["lead_time_1"]}',
    )
    recommendation = ProcurementRecommendation(
        plant_id=plant.id,
        material_id=material.id,
        recommended_qty=250.0,
        recommended_vendor_id=vendor.id,
        dispatch_date=date(2026, 8, 10),
        expected_arrival_date=date(2026, 8, 15),
        priority="HIGH",
        planning_mode="PROACTIVE",
        status="RECOMMENDED",
        reason="Trigger 1 hit",
    )
    prod_readiness = ProductionReadinessRecord(
        plant_id=plant.id,
        fg_material_id=material.id,
        status="LIMITED_PRODUCTION",
        blocking_rm_count=1,
        blocking_pm_count=0,
    )
    sim_run = SimulationRun(
        user_id=user.id,
        scenario_name="20% Demand Increase",
        input_params_json='{"demand_factor": 1.2}',
    )

    db_session.add_all([readiness, recommendation, prod_readiness, sim_run])
    db_session.commit()

    assert readiness.id is not None
    assert readiness.score == 92.5
    assert recommendation.id is not None
    assert recommendation.priority == "HIGH"
    assert prod_readiness.id is not None
    assert prod_readiness.status == "LIMITED_PRODUCTION"
    assert sim_run.id is not None
    assert sim_run.scenario_name == "20% Demand Increase"
