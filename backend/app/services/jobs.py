from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models.domain import Material, Plant
from app.db.models.job import JobRun
from app.services.forecasting.engine import generate_demand_forecast
from app.services.planning.engine import evaluate_material_planning
from app.services.reporting import (
    build_csv_export,
    build_xlsx_export,
    get_report_dataset,
)
from app.services.sap import get_sap_adapter


class JobError(AppError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__("JOB_ERROR", message, status_code)


VALID_JOB_TYPES = {
    "REPORT_EXPORT",
    "SAP_SYNC",
    "FORECAST_GENERATE",
    "PLANNING_RECALC",
}


def create_job(
    db: Session,
    job_type: str,
    user_id: int | None = None,
    payload: dict[str, Any] | None = None,
    custom_job_id_prefix: str = "JOB",
) -> JobRun:
    """Creates a durable JobRun record in PENDING status."""
    norm_type = job_type.upper()
    if norm_type not in VALID_JOB_TYPES:
        valid_str = ", ".join(sorted(VALID_JOB_TYPES))
        raise JobError(f"Unsupported job type '{job_type}'. Valid types: {valid_str}")

    job_id = f"{custom_job_id_prefix}-{uuid4().hex[:8].upper()}"
    job = JobRun(
        job_id=job_id,
        job_type=norm_type,
        status="PENDING",
        user_id=user_id,
        payload_json=json.dumps(payload) if payload else None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job_by_id(db: Session, job_id: str) -> JobRun:
    job = db.query(JobRun).filter(JobRun.job_id == job_id).first()
    if not job:
        raise JobError(f"Job with ID '{job_id}' not found.", 404)
    return job


def list_jobs(
    db: Session,
    job_type: str | None = None,
    status: str | None = None,
    user_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[JobRun], int]:
    query = db.query(JobRun)
    if job_type:
        query = query.filter(JobRun.job_type == job_type.upper())
    if status:
        query = query.filter(JobRun.status == status.upper())
    if user_id is not None:
        query = query.filter(JobRun.user_id == user_id)

    total = query.count()
    items = query.order_by(JobRun.id.desc()).offset(offset).limit(limit).all()
    return items, total


def execute_job(db: Session, job_id: str) -> JobRun:
    """Executes a job deterministically with state transitions and concurrency safety."""
    # Atomic claim / status check to prevent overlapping concurrent executions
    job = db.query(JobRun).filter(JobRun.job_id == job_id).with_for_update(of=JobRun).first()
    if not job:
        raise JobError(f"Job with ID '{job_id}' not found.", 404)

    if job.status == "RUNNING":
        raise JobError(f"Job '{job_id}' is already currently executing.", 409)

    if job.status == "COMPLETED":
        return job

    job.status = "RUNNING"
    job.started_at = datetime.now()
    job.error_message = None
    db.commit()

    payload = json.loads(job.payload_json) if job.payload_json else {}

    try:
        if job.job_type == "REPORT_EXPORT":
            _execute_report_export_job(db, job, payload)
        elif job.job_type == "SAP_SYNC":
            _execute_sap_sync_job(db, job)
        elif job.job_type == "FORECAST_GENERATE":
            _execute_forecast_generate_job(db, job, payload)
        elif job.job_type == "PLANNING_RECALC":
            _execute_planning_recalc_job(db, job, payload)

        job.status = "COMPLETED"
        job.completed_at = datetime.now()
        db.commit()
        db.refresh(job)
        return job
    except Exception as exc:
        db.rollback()
        # Re-fetch job object after rollback to record failure
        failed_job = db.query(JobRun).filter(JobRun.job_id == job_id).first()
        if failed_job:
            failed_job.status = "FAILED"
            failed_job.completed_at = datetime.now()
            failed_job.error_message = str(exc)
            db.commit()
            db.refresh(failed_job)
            return failed_job
        raise exc


def retry_job(db: Session, job_id: str) -> JobRun:
    """Resets a failed job to PENDING and re-runs execution."""
    job = get_job_by_id(db, job_id)
    if job.status != "FAILED":
        msg = f"Cannot retry job '{job_id}' in status '{job.status}'."
        raise JobError(msg)

    job.status = "PENDING"
    job.error_message = None
    db.commit()
    return execute_job(db, job_id)


def _execute_report_export_job(db: Session, job: JobRun, payload: dict[str, Any]) -> None:
    report_type = payload.get("report_type", "planning_summary")
    fmt = payload.get("format", "csv").lower()
    plant_code = payload.get("plant_code")
    material_code = payload.get("material_code")
    criticality_status = payload.get("criticality_status")
    status = payload.get("status")

    title, headers, rows = get_report_dataset(
        db, report_type, plant_code, material_code, criticality_status, status
    )

    clean_title = title.lower().replace(" ", "_")
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{clean_title}_{timestamp_str}.{fmt}"

    if fmt == "xlsx":
        content_bytes = build_xlsx_export(title, headers, rows)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        content_bytes = build_csv_export(headers, rows)
        media_type = "text/csv; charset=utf-8"

    job.binary_artifact = content_bytes
    job.result_json = json.dumps({
        "filename": filename,
        "media_type": media_type,
        "total_records": len(rows),
        "report_type": report_type,
        "format": fmt,
    })


def _execute_sap_sync_job(db: Session, job: JobRun) -> None:
    adapter = get_sap_adapter()
    synced_counts = adapter.sync_to_database(db)
    job.result_json = json.dumps({
        "adapter_mode": adapter.__class__.__name__,
        "synced_counts": synced_counts,
    })


def _execute_forecast_generate_job(db: Session, job: JobRun, payload: dict[str, Any]) -> None:
    plant_code = payload.get("plant_code")
    material_code = payload.get("material_code")

    plants_query = db.query(Plant)
    if plant_code:
        plants_query = plants_query.filter(Plant.code == plant_code)
    plants = plants_query.all()

    materials_query = db.query(Material)
    if material_code:
        materials_query = materials_query.filter(Material.code == material_code)
    materials = materials_query.all()

    processed = 0
    for p in plants:
        for m in materials:
            try:
                generate_demand_forecast(db, p.code, m.code)
                processed += 1
            except Exception:
                continue

    job.result_json = json.dumps({"processed_combinations": processed})


def _execute_planning_recalc_job(db: Session, job: JobRun, payload: dict[str, Any]) -> None:
    plant_code = payload.get("plant_code")
    material_code = payload.get("material_code")

    plants_query = db.query(Plant)
    if plant_code:
        plants_query = plants_query.filter(Plant.code == plant_code)
    plants = plants_query.all()

    materials_query = db.query(Material)
    if material_code:
        materials_query = materials_query.filter(Material.code == material_code)
    materials = materials_query.all()

    recalculated = 0
    for p in plants:
        for m in materials:
            try:
                evaluate_material_planning(db, p.code, m.code)
                recalculated += 1
            except Exception:
                continue

    job.result_json = json.dumps({"recalculated_combinations": recalculated})
