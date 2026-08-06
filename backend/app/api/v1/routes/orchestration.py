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


@router.get("/executions/telemetry")
def get_planning_execution_telemetry(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    plant_code: Annotated[str | None, Query(description="Target plant code filter")] = None,
) -> dict[str, Any]:
    """Retrieve execution metrics and telemetry statistics for monitoring."""
    history = get_planning_execution_history(db=db, plant_code=plant_code, limit=100)
    total_runs = len(history)
    successful = sum(1 for h in history if h.get("execution_status") == "SUCCESS")
    failed = sum(1 for h in history if h.get("execution_status") in ("FAILED", "BLOCKED"))
    durations = [h.get("duration_ms", 0.0) for h in history if h.get("duration_ms")]
    avg_duration = (sum(durations) / len(durations)) if durations else 0.0

    return {
        "total_executions": total_runs,
        "successful_executions": successful,
        "failed_or_blocked_executions": failed,
        "average_duration_ms": round(avg_duration, 2),
        "success_rate_percentage": round((successful / total_runs * 100.0), 1) if total_runs > 0 else 100.0,
    }


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
