from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models.user import User
from app.schemas.reporting import (
    ExportJobResponseSchema,
    ReportDatasetResponseSchema,
    ReportExportRequestSchema,
)
from app.services.reporting import (
    VALID_FORMATS,
    ReportingError,
    build_csv_export,
    build_xlsx_export,
    get_report_dataset,
)

router = APIRouter(prefix="/reports", tags=["reports"])

# In-memory registry for generated export jobs (REP-001/REP-003 boundary)
_export_cache: dict[str, dict[str, Any]] = {}


@router.get("", response_model=ReportDatasetResponseSchema)
def api_get_report_preview(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    report_type: Annotated[str, Query(description="Report type")] = "planning_summary",
    plant_code: Annotated[str | None, Query()] = None,
    material_code: Annotated[str | None, Query()] = None,
    criticality_status: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
) -> ReportDatasetResponseSchema:
    title, headers, rows = get_report_dataset(
        db, report_type, plant_code, material_code, criticality_status, status
    )
    return ReportDatasetResponseSchema(
        title=title,
        headers=headers,
        rows=rows,
        total_records=len(rows),
    )


@router.post("/exports", response_model=ExportJobResponseSchema)
def api_request_export(
    req: ReportExportRequestSchema,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ExportJobResponseSchema:
    if req.format.lower() not in VALID_FORMATS:
        raise ReportingError(f"Unsupported format '{req.format}'. Valid formats: csv, xlsx.", 400)

    title, headers, rows = get_report_dataset(
        db,
        req.report_type,
        req.plant_code,
        req.material_code,
        req.criticality_status,
        req.status,
    )

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_title = title.lower().replace(" ", "_")
    ext = req.format.lower()
    filename = f"{clean_title}_{timestamp_str}.{ext}"

    if ext == "xlsx":
        content_bytes = build_xlsx_export(title, headers, rows)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        content_bytes = build_csv_export(headers, rows)
        media_type = "text/csv; charset=utf-8"

    export_id = f"EXP-{uuid4().hex[:8].upper()}"
    download_url = f"/api/v1/reports/exports/{export_id}/download"

    _export_cache[export_id] = {
        "user_id": current_user.id,
        "filename": filename,
        "media_type": media_type,
        "content_bytes": content_bytes,
        "created_at": datetime.now().isoformat(),
        "report_type": req.report_type,
        "format": ext,
    }

    return ExportJobResponseSchema(
        export_id=export_id,
        report_type=req.report_type,
        format=ext,
        status="COMPLETED",
        created_at=datetime.now().isoformat(),
        download_url=download_url,
    )


@router.get("/exports/{export_id}/download")
def api_download_export(
    export_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    job = _export_cache.get(export_id)
    if not job:
        raise ReportingError(f"Export job with ID '{export_id}' not found.", 404)

    if job["user_id"] != current_user.id:
        raise ReportingError("Access denied to requested report export.", 403)

    return Response(
        content=job["content_bytes"],
        media_type=job["media_type"],
        headers={"Content-Disposition": f'attachment; filename="{job["filename"]}"'},
    )


@router.get("/download")
def api_direct_download_report(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    report_type: Annotated[str, Query()] = "planning_summary",
    format: Annotated[str, Query()] = "csv",
    plant_code: Annotated[str | None, Query()] = None,
    material_code: Annotated[str | None, Query()] = None,
    criticality_status: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
) -> Response:
    fmt = format.lower()
    if fmt not in VALID_FORMATS:
        raise ReportingError(f"Unsupported format '{format}'. Valid formats: csv, xlsx.", 400)

    title, headers, rows = get_report_dataset(
        db, report_type, plant_code, material_code, criticality_status, status
    )

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_title = title.lower().replace(" ", "_")
    filename = f"{clean_title}_{timestamp_str}.{fmt}"

    if fmt == "xlsx":
        content_bytes = build_xlsx_export(title, headers, rows)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        content_bytes = build_csv_export(headers, rows)
        media_type = "text/csv; charset=utf-8"

    return Response(
        content=content_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
