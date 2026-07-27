from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models.job import JobRun
from app.db.models.user import User
from app.schemas.job import JobCreateRequestSchema, JobListResponseSchema, JobRunResponseSchema
from app.services.jobs import create_job, execute_job, get_job_by_id, list_jobs, retry_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _serialize_job(job: JobRun) -> JobRunResponseSchema:
    return JobRunResponseSchema(
        id=job.id,
        job_id=job.job_id,
        job_type=job.job_type,
        status=job.status,
        user_id=job.user_id,
        payload_json=job.payload_json,
        result_json=job.result_json,
        error_message=job.error_message,
        created_at=job.created_at.isoformat() if job.created_at else "",
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
    )


@router.post("", response_model=JobRunResponseSchema)
def api_create_and_run_job(
    req: JobCreateRequestSchema,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobRunResponseSchema:
    job = create_job(db, req.job_type, current_user.id, req.payload)
    executed_job = execute_job(db, job.job_id)
    return _serialize_job(executed_job)


@router.get("", response_model=JobListResponseSchema)
def api_list_jobs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    job_type: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> JobListResponseSchema:
    items, total = list_jobs(db, job_type, status, user_id=None, limit=limit, offset=offset)
    return JobListResponseSchema(
        items=[_serialize_job(j) for j in items],
        total=total,
    )


@router.get("/{job_id}", response_model=JobRunResponseSchema)
def api_get_job(
    job_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobRunResponseSchema:
    job = get_job_by_id(db, job_id)
    return _serialize_job(job)


@router.post("/{job_id}/retry", response_model=JobRunResponseSchema)
def api_retry_job(
    job_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobRunResponseSchema:
    retried = retry_job(db, job_id)
    return _serialize_job(retried)
