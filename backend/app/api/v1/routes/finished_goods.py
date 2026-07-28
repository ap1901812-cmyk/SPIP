from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models.user import User
from app.schemas.finished_goods import (
    FGBOMExpansionResponse,
    FinishedGoodDetail,
    FinishedGoodSummary,
)
from app.services.finished_goods import FinishedGoodsService

router = APIRouter(prefix="/finished-goods", tags=["finished-goods"])


@router.get("", response_model=list[FinishedGoodSummary])
def list_finished_goods(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    plant_id: int | None = Query(None, description="Filter Finished Goods by plant ID"),
) -> list[FinishedGoodSummary]:
    return FinishedGoodsService.get_finished_goods(db, plant_id=plant_id)


@router.get("/{id}", response_model=FinishedGoodDetail)
def get_finished_good(
    id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FinishedGoodDetail:
    return FinishedGoodsService.get_finished_good_by_id(db, id)


@router.get("/{id}/bom", response_model=FGBOMExpansionResponse)
def get_finished_good_bom(
    id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FGBOMExpansionResponse:
    return FinishedGoodsService.get_fg_bom_expansion(db, id)
