from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.db.models.user import RoleEnum, User
from app.schemas.bom import BOMCreate, BOMDetailResponse, BOMResponse, BOMUpdate
from app.schemas.finished_goods import FGBOMExpansionResponse
from app.services.bom import BOMService
from app.services.finished_goods import FinishedGoodsService

router = APIRouter(prefix="/boms", tags=["boms"])

planner_or_admin_role = require_roles(RoleEnum.PLANNER, RoleEnum.ADMIN)
admin_role = require_roles(RoleEnum.ADMIN)


@router.get("", response_model=list[BOMDetailResponse])
def list_boms(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    fg_material_id: int | None = Query(None, description="Filter by FG material ID"),
    component_material_id: int | None = Query(None, description="Filter by Component material ID"),
    is_active: bool | None = Query(None, description="Filter by active status"),
) -> list[BOMDetailResponse]:
    boms = BOMService.get_boms(
        db,
        fg_material_id=fg_material_id,
        component_material_id=component_material_id,
        is_active=is_active,
    )
    return [BOMDetailResponse.model_validate(b) for b in boms]


@router.get("/expansion/{fg_id}", response_model=FGBOMExpansionResponse)
def get_fg_bom_expansion(
    fg_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FGBOMExpansionResponse:
    return FinishedGoodsService.get_fg_bom_expansion(db, fg_id)



@router.post("", response_model=BOMDetailResponse, status_code=status.HTTP_201_CREATED)
def create_bom(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(planner_or_admin_role)],
    bom_in: BOMCreate,
) -> BOMDetailResponse:
    bom = BOMService.create_bom(db, bom_in)
    return BOMDetailResponse.model_validate(bom)


@router.get("/{bom_id}", response_model=BOMDetailResponse)
def get_bom(
    bom_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BOMDetailResponse:
    bom = BOMService.get_bom_by_id(db, bom_id)
    return BOMDetailResponse.model_validate(bom)


@router.put("/{bom_id}", response_model=BOMDetailResponse)
def update_bom(
    bom_id: int,
    bom_in: BOMUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(planner_or_admin_role)],
) -> BOMDetailResponse:
    bom = BOMService.update_bom(db, bom_id, bom_in)
    return BOMDetailResponse.model_validate(bom)


@router.delete("/{bom_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_bom(
    bom_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(admin_role)],
) -> Response:
    BOMService.delete_bom(db, bom_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
