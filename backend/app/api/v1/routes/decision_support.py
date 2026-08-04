from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models.user import User
from app.services.planning.decision_support import (
    DecisionSupportSummary,
    get_decision_support_summary,
)
from app.services.planning.explainability import (
    ExplainabilityReport,
    get_explainability_report,
)

router = APIRouter(prefix="/decision-support", tags=["decision-support"])


@router.get(
    "/summary",
    response_model=DecisionSupportSummary,
    summary="Get Decision Support Summary",
    description="Provides planners with one consolidated decision explanation collecting outputs from all planning modules.",
)
def api_get_decision_support_summary(
    plant_code: str = Query(..., description="Plant code to summarize"),
    material_code: str | None = Query(None, description="Optional material code filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DecisionSupportSummary:
    return get_decision_support_summary(db=db, plant_code=plant_code, material_code=material_code)


@router.get(
    "/explainability",
    response_model=ExplainabilityReport,
    summary="Get Planning Explainability Report",
    description="Provides transparent explainability breakdown detailing source data, intermediate calculations, applied rules, and confidence scores.",
)
def api_get_explainability_report(
    plant_code: str = Query(..., description="Plant code to evaluate"),
    material_code: str = Query(..., description="Material code to evaluate"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExplainabilityReport:
    return get_explainability_report(db=db, plant_code=plant_code, material_code=material_code)
