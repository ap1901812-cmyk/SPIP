from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models.domain import Material, Plant
from app.db.models.user import User
from app.services.planning.dependency_intelligence import get_fg_dependency_matrix
from app.services.planning.production_readiness import evaluate_fg_production_readiness

router = APIRouter(prefix="/planning", tags=["production-readiness"])


@router.get("/production-readiness")
def get_production_readiness_evaluation(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    plant_code: Annotated[str, Query(description="Target plant code")],
    fg_material_code: Annotated[str, Query(description="Target Finished Good material code")],
) -> dict[str, Any]:
    """Evaluate 4-tier Production Readiness for a Finished Good combining RM Totality,

    PM Planning, Inventory Intelligence, and RMPM Statistical Planning.
    """
    res = evaluate_fg_production_readiness(
        db=db,
        plant_code=plant_code,
        fg_material_code=fg_material_code,
        user_id=current_user.id,
    )
    return res.model_dump()


@router.get("/materials/{material_code}/dependencies")
def get_material_dependency_matrix(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    material_code: str,
    plant_code: Annotated[str, Query(description="Target plant code")],
) -> dict[str, Any]:
    """Retrieve Dependency Matrix for a Finished Good showing RM Totality and PM BOM/Override dependencies."""
    plant = db.query(Plant).filter(Plant.code == plant_code).first()
    if not plant:
        return {"status": "ERROR", "message": f"Plant '{plant_code}' not found."}

    mat = db.query(Material).filter(Material.code == material_code).first()
    if not mat:
        return {"status": "ERROR", "message": f"Material '{material_code}' not found."}

    matrix = get_fg_dependency_matrix(db=db, plant_id=plant.id, fg_material_id=mat.id)
    return matrix.model_dump()
