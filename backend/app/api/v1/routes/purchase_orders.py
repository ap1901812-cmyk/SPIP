from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models.domain import Plant, PurchaseOrder
from app.db.models.user import User
from app.schemas.domain import PurchaseOrderResponse

router = APIRouter(prefix="/purchase-orders", tags=["purchase-orders"])


@router.get("", response_model=list[PurchaseOrderResponse])
def list_purchase_orders(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    plant_code: Annotated[str | None, Query(description="Filter by plant code")] = None,
) -> list[PurchaseOrderResponse]:
    query = db.query(PurchaseOrder)
    if plant_code:
        query = query.join(Plant).filter(Plant.code == plant_code)
    pos = query.all()
    return [PurchaseOrderResponse.model_validate(p) for p in pos]
