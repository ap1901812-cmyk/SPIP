from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated

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
from app.services.jobs import create_job, execute_job, get_job_by_id
from app.services.reporting import (
    VALID_FORMATS,
    ReportingError,
    build_csv_export,
    build_pdf_export,
    build_xlsx_export,
    get_report_dataset,
)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/export", summary="Direct Report File Download")
@router.get("/download", summary="Direct Report File Download Alias")
def api_download_report_export(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    report_type: str = Query("planning_summary", description="Report type"),
    format: str = Query("csv", description="Export format: csv, xlsx, or pdf"),
    plant_code: str | None = Query(None),
    material_code: str | None = Query(None),
    criticality_status: str | None = Query(None),
    status: str | None = Query(None),
) -> Response:
    norm_format = format.lower()
    if norm_format not in VALID_FORMATS:
        raise ReportingError(f"Unsupported format '{format}'. Valid formats: csv, xlsx, pdf.", 400)

    title, headers, rows = get_report_dataset(
        db, report_type, plant_code, material_code, criticality_status, status
    )

    clean_name = report_type.lower().replace(" ", "_")
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    if norm_format == "csv":
        data = build_csv_export(headers, rows)
        media_type = "text/csv"
        filename = f"{clean_name}_{ts}.csv"
    elif norm_format == "xlsx":
        data = build_xlsx_export(title, headers, rows)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{clean_name}_{ts}.xlsx"
    else:
        data = build_pdf_export(title, headers, rows)
        media_type = "application/pdf"
        filename = f"{clean_name}_{ts}.pdf"

    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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

    payload = {
        "report_type": req.report_type,
        "format": req.format.lower(),
        "plant_code": req.plant_code,
        "material_code": req.material_code,
        "criticality_status": req.criticality_status,
        "status": req.status,
    }

    # Create durable PostgreSQL JobRun record (Phase 10 durable export job workflow)
    job = create_job(
        db,
        job_type="REPORT_EXPORT",
        user_id=current_user.id,
        payload=payload,
        custom_job_id_prefix="EXP",
    )
    job = execute_job(db, job.job_id)

    download_url = f"/api/v1/reports/exports/{job.job_id}/download"

    return ExportJobResponseSchema(
        export_id=job.job_id,
        report_type=req.report_type,
        format=req.format.lower(),
        status=job.status,
        created_at=job.created_at.isoformat(),
        download_url=download_url,
    )


@router.get("/exports/{export_id}/download")
def api_download_export(
    export_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    job = get_job_by_id(db, export_id)

    if job.user_id != current_user.id:
        raise ReportingError("Access denied to requested report export.", 403)

    if not job.binary_artifact:
        raise ReportingError(f"Export artifact for job '{export_id}' is empty or unavailable.", 404)

    meta = json.loads(job.result_json) if job.result_json else {}
    fmt = meta.get("format", "xlsx" if export_id.endswith("-XLSX") else "csv").lower()
    default_media_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if fmt == "xlsx"
        else "text/csv; charset=utf-8"
    )
    media_type = meta.get("media_type", default_media_type)
    filename = meta.get("filename", f"{export_id}.{fmt}")

    return Response(
        content=job.binary_artifact,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
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
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
