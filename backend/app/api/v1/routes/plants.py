from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models.domain import Plant
from app.db.models.user import User
from app.schemas.domain import PlantResponse

router = APIRouter(prefix="/plants", tags=["plants"])


@router.get("", response_model=list[PlantResponse])
def list_plants(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[PlantResponse]:
    plants = db.query(Plant).all()
    return [PlantResponse.model_validate(p) for p in plants]
