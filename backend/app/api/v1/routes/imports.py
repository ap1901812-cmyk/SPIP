from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.db.models.user import RoleEnum, User
from app.services.ingestion import IngestionResult, ingest_csv_data, ingest_xlsx_data

router = APIRouter(prefix="/imports", tags=["imports"])

planner_or_admin_role = require_roles(RoleEnum.PLANNER, RoleEnum.ADMIN)


@router.post(
    "/csv",
    response_model=IngestionResult,
    dependencies=[Depends(planner_or_admin_role)],
)
async def import_csv(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(planner_or_admin_role)],
    file: UploadFile = File(...),
    entity_type: str = Query(..., description="Target entity type: 'consumption' or 'inventory'"),
) -> IngestionResult:
    content = await file.read()
    return ingest_csv_data(db=db, entity_type=entity_type, file_content=content)


@router.post(
    "/xlsx",
    response_model=IngestionResult,
    dependencies=[Depends(planner_or_admin_role)],
)
async def import_xlsx(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(planner_or_admin_role)],
    file: UploadFile = File(...),
    entity_type: str = Query(..., description="Target entity type: 'consumption' or 'inventory'"),
) -> IngestionResult:
    content = await file.read()
    return ingest_xlsx_data(db=db, entity_type=entity_type, file_content=content)
