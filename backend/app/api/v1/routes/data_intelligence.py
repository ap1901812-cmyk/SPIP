from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.db.models.audit import AuditLog
from app.db.models.user import RoleEnum, User
from app.services.data_intelligence.quality_scanner import DataQualitySummary
from app.services.data_intelligence.service import EnterpriseDataIntelligenceService

router = APIRouter(prefix="/data-intelligence", tags=["data-intelligence"])

planner_or_admin_role = require_roles(RoleEnum.PLANNER, RoleEnum.ADMIN)


class SAPSyncRequest(BaseModel):
    plant_code: str
    consumption_records: list[dict[str, Any]] = []
    inventory_records: list[dict[str, Any]] = []
    purchase_orders: list[dict[str, Any]] = []


@router.post(
    "/ingest-batch",
    response_model=DataQualitySummary,
    dependencies=[Depends(planner_or_admin_role)],
)
async def ingest_batch(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(planner_or_admin_role)],
    files: list[UploadFile] = File(...),
) -> DataQualitySummary:
    """Multi-file data ingestion with automatic file recognition, cross-file analysis,

    duplicate detection, auto master generation, and data quality summary reporting.
    """
    file_payloads: list[tuple[str, bytes]] = []
    for f in files:
        content = await f.read()
        file_payloads.append((f.filename or "uploaded_file", content))

    service = EnterpriseDataIntelligenceService(db=db, user_id=current_user.id)
    return service.process_batch(file_payloads)


@router.get(
    "/scan-results",
    dependencies=[Depends(planner_or_admin_role)],
)
def get_scan_results(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(planner_or_admin_role)],
) -> dict[str, Any]:
    """Retrieve historical audit logs for auto-generated master records."""
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.action.like("AUTO_GENERATE_%"))
        .order_by(AuditLog.created_at.desc())
        .limit(100)
        .all()
    )
    return {
        "auto_generated_count": len(logs),
        "audit_logs": [
            {
                "id": log.id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details": log.details,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
    }


@router.post(
    "/sap-sync",
    response_model=DataQualitySummary,
    dependencies=[Depends(planner_or_admin_role)],
)
def sap_sync(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(planner_or_admin_role)],
    request: SAPSyncRequest,
) -> DataQualitySummary:
    """Ingest operational data from SAP payloads with auto master generation."""
    service = EnterpriseDataIntelligenceService(db=db, user_id=current_user.id)
    # Convert SAP payload to batch format
    files: list[tuple[str, bytes]] = []

    if request.consumption_records:
        import json

        import pandas as pd

        df = pd.DataFrame(request.consumption_records)
        files.append(("sap_consumption.csv", df.to_csv(index=False).encode("utf-8")))

    if request.inventory_records:
        import pandas as pd

        df = pd.DataFrame(request.inventory_records)
        files.append(("sap_inventory.csv", df.to_csv(index=False).encode("utf-8")))

    if request.purchase_orders:
        import pandas as pd

        df = pd.DataFrame(request.purchase_orders)
        files.append(("sap_purchase_orders.csv", df.to_csv(index=False).encode("utf-8")))

    return service.process_batch(files)
