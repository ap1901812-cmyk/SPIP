from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models.domain import ConsumptionHistory, Plant
from app.db.models.user import User
from app.schemas.domain import ConsumptionResponse

router = APIRouter(prefix="/consumption", tags=["consumption"])


@router.get("", response_model=list[ConsumptionResponse])
def list_consumption(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    plant_code: Annotated[str | None, Query(description="Filter by plant code")] = None,
) -> list[ConsumptionResponse]:
    query = db.query(ConsumptionHistory)
    if plant_code:
        query = query.join(Plant).filter(Plant.code == plant_code)
    records = query.order_by(ConsumptionHistory.consumption_date.desc()).all()
    return [ConsumptionResponse.model_validate(c) for c in records]
