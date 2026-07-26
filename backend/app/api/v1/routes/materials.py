from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models.domain import Material
from app.db.models.user import User
from app.schemas.domain import MaterialResponse

router = APIRouter(prefix="/materials", tags=["materials"])


@router.get("", response_model=list[MaterialResponse])
def list_materials(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[MaterialResponse]:
    materials = db.query(Material).all()
    return [MaterialResponse.model_validate(m) for m in materials]
