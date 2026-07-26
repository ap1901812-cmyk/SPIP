from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models.domain import InventorySnapshot, Plant
from app.db.models.user import User
from app.schemas.domain import InventorySnapshotResponse

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("", response_model=list[InventorySnapshotResponse])
def list_inventory(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    plant_code: Annotated[str | None, Query(description="Filter by plant code")] = None,
) -> list[InventorySnapshotResponse]:
    query = db.query(InventorySnapshot)
    if plant_code:
        query = query.join(Plant).filter(Plant.code == plant_code)
    snapshots = query.all()
    return [InventorySnapshotResponse.model_validate(s) for s in snapshots]
