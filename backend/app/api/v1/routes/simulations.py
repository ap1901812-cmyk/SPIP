from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.db.models.user import RoleEnum, User
from app.services.planning.simulation import (
    ScenarioOverrides,
    SimulationRunItem,
    get_simulation_detail,
    get_simulation_history,
    run_what_if_simulation,
)

router = APIRouter(prefix="/simulations", tags=["simulations"])


class RunSimulationRequest(BaseModel):
    scenario_name: str = Field(..., description="Scenario identifier name")
    plant_code: str = Field(..., description="Plant code to simulate")
    material_code: str | None = Field(None, description="Optional material code filter")
    overrides: ScenarioOverrides = Field(default_factory=ScenarioOverrides)


@router.post(
    "/run",
    response_model=SimulationRunItem,
    summary="Run What-If Simulation",
    description="Executes isolated planning scenario with parameter overrides without modifying production records.",
)
def api_run_what_if_simulation(
    req: RunSimulationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleEnum.ADMIN.value, RoleEnum.PLANNER.value, RoleEnum.MANAGER_APPROVER.value)
    ),
) -> SimulationRunItem:
    return run_what_if_simulation(
        db=db,
        user_id=current_user.id,
        scenario_name=req.scenario_name,
        plant_code=req.plant_code,
        material_code=req.material_code,
        overrides=req.overrides,
    )


@router.get(
    "",
    summary="List Simulation History",
    description="Retrieves history of past What-If scenario simulations.",
)
def api_list_simulations(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    return get_simulation_history(db=db, user_id=current_user.id, limit=limit)


@router.get(
    "/{simulation_id}",
    summary="Get Simulation Detail",
    description="Retrieves detailed inputs and outputs for a specific What-If simulation run.",
)
def api_get_simulation_detail(
    simulation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return get_simulation_detail(db=db, simulation_id=simulation_id)
