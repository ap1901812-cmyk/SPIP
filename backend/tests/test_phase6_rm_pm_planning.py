from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.db.models.domain import BOM, Material, PMOverride, Plant, RMTotalityMapping
from app.db.models.user import RoleEnum, User, UserRole
from app.services.planning.pm_planning import (
    create_or_update_pm_override,
    evaluate_pm_planning,
)
from app.services.planning.rm_totality import build_and_evaluate_rm_totality


def _seed_planner(db: Session) -> dict[str, str]:
    user = User(
        email="planner_p6@example.com",
        full_name="Phase6 Planner",
        hashed_password=hash_password("Pass123!"),
        is_active=True,
    )
    user.roles.append(UserRole(role_name=RoleEnum.PLANNER.value))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user_id=user.id, email=user.email, roles=[RoleEnum.PLANNER.value])
    return {"Authorization": f"Bearer {token}"}


def test_rm_totality_mapping_and_planning(db_session: Session) -> None:
    plant = Plant(code="P-RM-1", name="RM Plant")
    rm_mat = Material(code="RM-100", description="Raw Material 100", material_type="RM", base_uom="KG")
    fg1 = Material(code="FG-100", description="Finished Good 1", material_type="FG", base_uom="EA")
    fg2 = Material(code="FG-200", description="Finished Good 2", material_type="FG", base_uom="EA")
    db_session.add_all([plant, rm_mat, fg1, fg2])
    db_session.commit()

    bom1 = BOM(fg_material_id=fg1.id, component_material_id=rm_mat.id, required_quantity=2.0)
    bom2 = BOM(fg_material_id=fg2.id, component_material_id=rm_mat.id, required_quantity=3.0)
    db_session.add_all([bom1, bom2])
    db_session.commit()

    # Run RM Totality Planning
    res = build_and_evaluate_rm_totality(db_session, plant.id, rm_mat.id, final_resolved_requirement=500.0)

    assert res.rm_code == "RM-100"
    assert res.total_rm_requirement == 500.0
    assert "RM_TOTALITY_GROUP_RM-100" in res.totality_group_name
    assert len(res.contributing_fgs) == 2
    assert "RM Totality Planning calculated total RM requirement" in res.planning_explanation

    # Verify RMTotalityMapping persisted in database
    mapping = (
        db_session.query(RMTotalityMapping)
        .filter(RMTotalityMapping.plant_id == plant.id, RMTotalityMapping.rm_material_id == rm_mat.id)
        .first()
    )
    assert mapping is not None


def test_pm_planning_and_override_workflow(db_session: Session) -> None:
    plant = Plant(code="P-PM-1", name="PM Plant")
    pm_mat = Material(code="PM-100", description="Packaging Material 100", material_type="PM", base_uom="BOX")
    fg_mat = Material(code="FG-300", description="Finished Good 3", material_type="FG", base_uom="EA")
    db_session.add_all([plant, pm_mat, fg_mat])
    db_session.commit()

    bom = BOM(fg_material_id=fg_mat.id, component_material_id=pm_mat.id, required_quantity=1.0)
    db_session.add(bom)
    db_session.commit()

    # 1. Default BOM Planning
    res_bom = evaluate_pm_planning(db_session, plant.id, pm_mat.id, fg_mat.id, fg_requirement=100.0)
    assert res_bom.bom_quantity == 100.0
    assert res_bom.quantity_used_for_planning == 100.0
    assert res_bom.is_overridden is False

    # 2. Set PM Override ratio = 1.25
    ov = create_or_update_pm_override(
        db=db_session,
        plant_id=plant.id,
        fg_material_id=fg_mat.id,
        pm_material_id=pm_mat.id,
        override_ratio=1.25,
        notes="Bulk order safety multiplier",
    )
    assert ov.override_ratio == 1.25

    # 3. Overridden PM Planning
    res_ov = evaluate_pm_planning(db_session, plant.id, pm_mat.id, fg_mat.id, fg_requirement=100.0)
    assert res_ov.bom_quantity == 100.0
    assert res_ov.override_quantity == 125.0  # 100 * 1.25
    assert res_ov.quantity_used_for_planning == 125.0
    assert res_ov.is_overridden is True
    assert "Planner Override ratio" in res_ov.planning_explanation


def test_pm_override_api_endpoints(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = _seed_planner(db_session)

    plant = Plant(code="P-P6-API", name="P6 API Plant")
    pm_mat = Material(code="PM-API-1", description="PM API", material_type="PM", base_uom="BOX")
    fg_mat = Material(code="FG-API-1", description="FG API", material_type="FG", base_uom="EA")
    db_session.add_all([plant, pm_mat, fg_mat])
    db_session.commit()

    # 1. POST /api/v1/planning/pm-overrides
    res_post = client.post(
        "/api/v1/planning/pm-overrides",
        json={
            "plant_code": "P-P6-API",
            "fg_material_code": "FG-API-1",
            "pm_material_code": "PM-API-1",
            "override_ratio": 1.5,
            "notes": "Testing PM override API",
        },
        headers=headers,
    )
    assert res_post.status_code == 200
    data_post = res_post.json()
    assert data_post["override_ratio"] == 1.5

    # 2. GET /api/v1/planning/pm-overrides
    res_get = client.get("/api/v1/planning/pm-overrides?plant_code=P-P6-API", headers=headers)
    assert res_get.status_code == 200
    data_get = res_get.json()
    assert len(data_get) >= 1
    assert data_get[0]["pm_material_code"] == "PM-API-1"

    # 3. GET /api/v1/planning/materials/{material_code}
    res_plan = client.get("/api/v1/planning/materials/PM-API-1?plant_code=P-P6-API", headers=headers)
    assert res_plan.status_code == 200
    data_plan = res_plan.json()
    assert data_plan["is_pm_overridden"] is True
    assert data_plan["pm_override_ratio"] == 1.5
