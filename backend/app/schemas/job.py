from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class JobCreateRequestSchema(BaseModel):
    job_type: Literal["REPORT_EXPORT", "SAP_SYNC", "FORECAST_GENERATE", "PLANNING_RECALC"]
    payload: dict[str, Any] | None = None


class JobRunResponseSchema(BaseModel):
    id: int
    job_id: str
    job_type: str
    status: str
    user_id: int | None = None
    payload_json: str | None = None
    result_json: str | None = None
    error_message: str | None = None
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None


class JobListResponseSchema(BaseModel):
    items: list[JobRunResponseSchema]
    total: int
