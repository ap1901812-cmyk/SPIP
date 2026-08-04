from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.db.models.user import RoleEnum, User
from app.services.planning.readiness import PlanningReadinessEngine, PlanningReadinessReport

router = APIRouter(prefix="/planning/readiness", tags=["planning-readiness"])

planner_or_admin_role = require_roles(RoleEnum.PLANNER, RoleEnum.ADMIN)


class AcknowledgeReadinessRequest(BaseModel):
    plant_code: str


@router.get(
    "",
    response_model=PlanningReadinessReport,
    dependencies=[Depends(planner_or_admin_role)],
)
def get_planning_readiness(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(planner_or_admin_role)],
    plant_code: str = Query(..., description="Target plant code to evaluate readiness"),
) -> PlanningReadinessReport:
    """Evaluate current planning readiness score, constraint issues, decision state, and resolution steps for a plant."""
    engine = PlanningReadinessEngine(db=db, user_id=current_user.id)
    return engine.evaluate_readiness(plant_code=plant_code)


@router.get(
    "/history",
    dependencies=[Depends(planner_or_admin_role)],
)
def get_planning_readiness_history(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(planner_or_admin_role)],
    plant_code: str = Query(..., description="Target plant code"),
    limit: int = Query(20, ge=1, le=100),
) -> list[dict[str, Any]]:
    """Retrieve historical planning readiness scores for a plant."""
    engine = PlanningReadinessEngine(db=db, user_id=current_user.id)
    return engine.get_readiness_history(plant_code=plant_code, limit=limit)


@router.post(
    "/acknowledge",
    response_model=PlanningReadinessReport,
    dependencies=[Depends(planner_or_admin_role)],
)
def acknowledge_planning_readiness(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(planner_or_admin_role)],
    request: AcknowledgeReadinessRequest,
) -> PlanningReadinessReport:
    """Allow planner to acknowledge warning-level planning readiness issues for a plant."""
    engine = PlanningReadinessEngine(db=db, user_id=current_user.id)
    return engine.acknowledge_warnings(plant_code=request.plant_code, user_email=current_user.email)
