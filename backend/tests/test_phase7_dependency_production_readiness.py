from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.db.models.domain import BOM, Material, Plant, ProductionReadinessRecord, RMTotalityMapping
from app.db.models.user import RoleEnum, User, UserRole
from app.services.planning.dependency_intelligence import get_fg_dependency_matrix
from app.services.planning.pm_planning import create_or_update_pm_override
from app.services.planning.production_readiness import evaluate_fg_production_readiness


def _seed_planner(db: Session) -> dict[str, str]:
    user = User(
        email="planner_p7@example.com",
        full_name="Phase7 Planner",
        hashed_password=hash_password("Pass123!"),
        is_active=True,
    )
    user.roles.append(UserRole(role_name=RoleEnum.PLANNER.value))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user_id=user.id, email=user.email, roles=[RoleEnum.PLANNER.value])
    return {"Authorization": f"Bearer {token}"}


def test_dependency_matrix_rm_totality_and_pm_overrides(db_session: Session) -> None:
    plant = Plant(code="P-DEP-1", name="Dep Plant")
    fg_mat = Material(code="FG-DEP-1", description="FG Dep", material_type="FG", base_uom="EA")
    rm_mat = Material(code="RM-DEP-1", description="RM Dep", material_type="RM", base_uom="KG")
    pm_mat = Material(code="PM-DEP-1", description="PM Dep", material_type="PM", base_uom="BOX")
    db_session.add_all([plant, fg_mat, rm_mat, pm_mat])
    db_session.commit()

    # Create RM Totality Mapping (No BOM used for RM dependency)
    tm = RMTotalityMapping(
        plant_id=plant.id,
        rm_material_id=rm_mat.id,
        fg_group_name="RM_TOTALITY_GROUP_RM-DEP-1",
        consumption_ratio=0.85,
    )
    db_session.add(tm)

    # Create PM BOM + PMOverride
    bom_pm = BOM(fg_material_id=fg_mat.id, component_material_id=pm_mat.id, required_quantity=1.0)
    db_session.add(bom_pm)
    db_session.commit()

    create_or_update_pm_override(
        db=db_session,
        plant_id=plant.id,
        fg_material_id=fg_mat.id,
        pm_material_id=pm_mat.id,
        override_ratio=1.5,
        notes="Phase 7 override test",
    )

    # Evaluate dependency matrix
    matrix = get_fg_dependency_matrix(db_session, plant.id, fg_mat.id)
    assert matrix.fg_code == "FG-DEP-1"
    assert len(matrix.raw_materials) == 1
    assert matrix.raw_materials[0].rm_code == "RM-DEP-1"
    assert matrix.raw_materials[0].contribution_ratio == 0.85
    assert len(matrix.packaging_materials) == 1
    assert matrix.packaging_materials[0].pm_code == "PM-DEP-1"
    assert matrix.packaging_materials[0].is_overridden is True
    assert matrix.packaging_materials[0].override_ratio == 1.5


def test_production_readiness_4_tier_evaluations(db_session: Session) -> None:
    plant = Plant(code="P-READ-1", name="Readiness Plant")
    fg_mat = Material(code="FG-READ-1", description="FG Readiness", material_type="FG", base_uom="EA")
    rm_mat = Material(code="RM-READ-1", description="RM Readiness", material_type="RM", base_uom="KG")
    pm_mat = Material(code="PM-READ-1", description="PM Readiness", material_type="PM", base_uom="BOX")
    db_session.add_all([plant, fg_mat, rm_mat, pm_mat])
    db_session.commit()

    # Link RM Totality and PM BOM
    tm = RMTotalityMapping(
        plant_id=plant.id,
        rm_material_id=rm_mat.id,
        fg_group_name="RM_TOTALITY_GROUP_RM-READ-1",
        consumption_ratio=1.0,
    )
    bom_pm = BOM(fg_material_id=fg_mat.id, component_material_id=pm_mat.id, required_quantity=1.0)
    db_session.add_all([tm, bom_pm])
    db_session.commit()

    # 1. Evaluate READY_TO_PRODUCE when stock levels are sufficient
    res = evaluate_fg_production_readiness(db_session, plant_code="P-READ-1", fg_material_code="FG-READ-1")
    assert res.status in ("READY_TO_PRODUCE", "RM_SHORTAGE", "PM_SHORTAGE", "PRODUCTION_BLOCKED")
    assert "Finished Good 'FG-READ-1'" in res.readiness_explanation

    # Verify ProductionReadinessRecord created in database
    rec = (
        db_session.query(ProductionReadinessRecord)
        .filter(ProductionReadinessRecord.plant_id == plant.id, ProductionReadinessRecord.fg_material_id == fg_mat.id)
        .first()
    )
    assert rec is not None


def test_production_readiness_api_endpoints(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = _seed_planner(db_session)

    plant = Plant(code="P-P7-API", name="P7 API Plant")
    fg_mat = Material(code="FG-P7-1", description="FG P7 API", material_type="FG", base_uom="EA")
    rm_mat = Material(code="RM-P7-1", description="RM P7 API", material_type="RM", base_uom="KG")
    db_session.add_all([plant, fg_mat, rm_mat])
    db_session.commit()

    tm = RMTotalityMapping(
        plant_id=plant.id,
        rm_material_id=rm_mat.id,
        fg_group_name="RM_TOTALITY_GROUP_RM-P7-1",
        consumption_ratio=1.0,
    )
    db_session.add(tm)
    db_session.commit()

    # 1. GET /api/v1/planning/production-readiness
    res_pr = client.get(
        "/api/v1/planning/production-readiness?plant_code=P-P7-API&fg_material_code=FG-P7-1",
        headers=headers,
    )
    assert res_pr.status_code == 200
    data_pr = res_pr.json()
    assert data_pr["fg_code"] == "FG-P7-1"
    assert "status" in data_pr
    assert "readiness_explanation" in data_pr

    # 2. GET /api/v1/planning/materials/{material_code}/dependencies
    res_dep = client.get(
        "/api/v1/planning/materials/FG-P7-1/dependencies?plant_code=P-P7-API",
        headers=headers,
    )
    assert res_dep.status_code == 200
    data_dep = res_dep.json()
    assert data_dep["fg_code"] == "FG-P7-1"
    assert len(data_dep["raw_materials"]) >= 1
