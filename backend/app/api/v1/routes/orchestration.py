from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models.user import User
from app.services.planning.orchestrator import (
    execute_full_planning_pipeline,
    get_planning_execution_details,
    get_planning_execution_history,
)

router = APIRouter(prefix="/planning", tags=["planning-orchestrator"])


class ExecutePlanningPipelineRequest(BaseModel):
    plant_code: str = Field(..., description="Target plant code")
    material_code: str = Field(..., description="Target material code")
    horizon_days: int = Field(30, ge=1, le=365, description="Forecast horizon days")


@router.post("/execute")
def execute_planning_pipeline_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    request: ExecutePlanningPipelineRequest,
) -> dict[str, Any]:
    """Execute the full 11-step SPIP V2 Central Planning Pipeline for a plant/material."""
    try:
        res = execute_full_planning_pipeline(
            db=db,
            plant_code=request.plant_code,
            material_code=request.material_code,
            horizon_days=request.horizon_days,
            user_id=current_user.id,
        )
        return res.model_dump()
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err


@router.get("/executions")
def list_planning_execution_history(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    plant_code: Annotated[str | None, Query(description="Target plant code filter")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[dict[str, Any]]:
    """Retrieve planning pipeline execution logs."""
    return get_planning_execution_history(db=db, plant_code=plant_code, limit=limit)


@router.get("/executions/{execution_id}")
def get_planning_execution_report(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    execution_id: int,
) -> dict[str, Any]:
    """Retrieve detailed execution report for a specific pipeline execution run."""
    details = get_planning_execution_details(db=db, execution_id=execution_id)
    if not details:
        raise HTTPException(status_code=404, detail=f"Execution run ID {execution_id} not found.")
    return details
