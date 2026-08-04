from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.db.models.user import RoleEnum, User
from app.services.planning.procurement import (
    ProcurementRecommendationSummary,
    generate_procurement_recommendations,
    get_procurement_recommendation_by_id,
    get_procurement_recommendation_history,
    refresh_procurement_recommendations,
)

router = APIRouter(prefix="/planning/procurement-recommendations", tags=["procurement-recommendations"])


class GenerateRecommendationsRequest(BaseModel):
    plant_code: str = Field(..., description="Plant code to evaluate")
    material_code: str | None = Field(None, description="Optional material code filter")
    horizon_days: int = Field(15, ge=1, le=180, description="Planning horizon in days")
    planning_mode: str = Field("PROACTIVE", description="Planning mode: PROACTIVE or REACTIVE")


class RefreshRecommendationsRequest(BaseModel):
    plant_code: str = Field(..., description="Plant code to refresh recommendations for")


@router.post(
    "/generate",
    response_model=ProcurementRecommendationSummary,
    summary="Generate Procurement Recommendations",
    description="Converts planning pipeline results into actionable procurement recommendations (Proactive or Reactive mode).",
)
def api_generate_procurement_recommendations(
    req: GenerateRecommendationsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleEnum.ADMIN.value, RoleEnum.PLANNER.value, RoleEnum.MANAGER_APPROVER.value)
    ),
) -> ProcurementRecommendationSummary:
    return generate_procurement_recommendations(
        db=db,
        plant_code=req.plant_code,
        material_code=req.material_code,
        horizon_days=req.horizon_days,
        planning_mode=req.planning_mode,
        user_id=current_user.id,
    )


@router.post(
    "/refresh",
    response_model=ProcurementRecommendationSummary,
    summary="Manual Recommendation Refresh",
    description="Triggers a dynamic refresh of procurement recommendations for a plant.",
)
def api_refresh_procurement_recommendations(
    req: RefreshRecommendationsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleEnum.ADMIN.value, RoleEnum.PLANNER.value, RoleEnum.MANAGER_APPROVER.value)
    ),
) -> ProcurementRecommendationSummary:
    return refresh_procurement_recommendations(
        db=db, plant_code=req.plant_code, user_id=current_user.id
    )


@router.get(
    "",
    summary="List Recommendation History",
    description="Retrieves history of generated procurement recommendations for a plant.",
)
def api_list_procurement_recommendations(
    plant_code: str = Query(..., description="Plant code filter"),
    material_code: str | None = Query(None, description="Optional material code filter"),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    return get_procurement_recommendation_history(
        db=db, plant_code=plant_code, material_code=material_code, limit=limit
    )


@router.get(
    "/{recommendation_id}",
    summary="Get Recommendation Details",
    description="Retrieves recommendation details and full explainability payload.",
)
def api_get_procurement_recommendation_detail(
    recommendation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return get_procurement_recommendation_by_id(db=db, recommendation_id=recommendation_id)
