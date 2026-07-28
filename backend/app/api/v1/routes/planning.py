from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models.domain import Material, Plant
from app.db.models.user import User
from app.schemas.fg_planning import (
    FGPlanningRequest,
    FGPlanningResult,
    RecommendationSummary,
    ShortageSummary,
)
from app.schemas.planning import PlanningCalculationResult
from app.services.planning import FGPlanningService, evaluate_material_planning

router = APIRouter(prefix="/planning", tags=["planning"])


@router.post("/run", response_model=FGPlanningResult)
def run_fg_planning(
    request: FGPlanningRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FGPlanningResult:
    return FGPlanningService.run_planning(db, request)


@router.get("/shortages", response_model=ShortageSummary)
def get_material_shortage_summary(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    plant_code: Annotated[str | None, Query(description="Filter shortages by plant code")] = None,
) -> ShortageSummary:
    return FGPlanningService.get_shortage_summary(db, plant_code=plant_code)


@router.get("/recommendations", response_model=RecommendationSummary)
def get_procurement_recommendation_summary(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    plant_code: Annotated[str | None, Query(description="Filter recommendations by plant code")] = None,
) -> RecommendationSummary:
    return FGPlanningService.get_recommendation_summary(db, plant_code=plant_code)


@router.get("/materials/{material_code}", response_model=PlanningCalculationResult)
def get_material_planning_evaluation(
    material_code: str,
    plant_code: Annotated[str, Query(description="Target plant code")],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PlanningCalculationResult:
    return evaluate_material_planning(db=db, plant_code=plant_code, material_code=material_code)


@router.get("/summary", response_model=list[PlanningCalculationResult])
def get_planning_summary(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    plant_code: Annotated[str | None, Query(description="Filter by plant code")] = None,
) -> list[PlanningCalculationResult]:
    query_plants = db.query(Plant)
    if plant_code:
        query_plants = query_plants.filter(Plant.code == plant_code)
    plants = query_plants.all()

    materials = db.query(Material).all()

    results: list[PlanningCalculationResult] = []
    for plant in plants:
        for mat in materials:
            try:
                res = evaluate_material_planning(
                    db=db, plant_code=plant.code, material_code=mat.code
                )
                results.append(res)
            except Exception:
                continue

    return results

