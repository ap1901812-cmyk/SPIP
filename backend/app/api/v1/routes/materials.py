from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models.domain import Material
from app.db.models.user import User
from app.schemas.dependency import MaterialDependencyResponse, WhereUsedResponse
from app.schemas.domain import MaterialResponse
from app.services.dependency import DependencyService

router = APIRouter(prefix="/materials", tags=["materials"])


@router.get("", response_model=list[MaterialResponse])
def list_materials(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    material_type: str | None = Query(None, description="Filter materials by type (e.g. FG, RM, PM)"),
) -> list[MaterialResponse]:
    query = db.query(Material)
    if material_type:
        query = query.filter(Material.material_type == material_type)
    materials = query.all()
    return [MaterialResponse.model_validate(m) for m in materials]


@router.get("/{id}/where-used", response_model=WhereUsedResponse)
def get_material_where_used(
    id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WhereUsedResponse:
    return DependencyService.get_where_used(db, id)


@router.get("/{id}/dependencies", response_model=MaterialDependencyResponse)
def get_material_dependencies(
    id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MaterialDependencyResponse:
    return DependencyService.get_material_dependencies(db, id)


