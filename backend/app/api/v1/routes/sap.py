from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.core.config import get_settings
from app.db.models.user import RoleEnum, User
from app.services.sap import get_sap_adapter

router = APIRouter(prefix="/sap", tags=["sap"])

planner_or_admin_role = require_roles(RoleEnum.PLANNER, RoleEnum.ADMIN)


@router.get("/status")
def get_sap_status(
    current_user: Annotated[User, Depends(planner_or_admin_role)],
) -> dict[str, Any]:
    cfg = get_settings()
    return {
        "adapter_mode": cfg.sap_adapter_mode,
        "is_mock": cfg.sap_adapter_mode == "mock",
        "message": "SAP adapter interface active in mock demo mode"
        if cfg.sap_adapter_mode == "mock"
        else "Real SAP transport configured",
    }


@router.post("/sync", dependencies=[Depends(planner_or_admin_role)])
def sync_sap_data(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(planner_or_admin_role)],
) -> dict[str, Any]:
    adapter = get_sap_adapter()
    counts = adapter.sync_to_database(db)
    return {
        "status": "success",
        "adapter_mode": get_settings().sap_adapter_mode,
        "synced_counts": counts,
    }
