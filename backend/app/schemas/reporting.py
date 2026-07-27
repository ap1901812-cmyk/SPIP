from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class ReportExportRequestSchema(BaseModel):
    report_type: Literal[
        "planning_summary",
        "inventory_planning",
        "forecast_summary",
        "demand_forecasting",
        "allocations",
        "vendor_allocations",
    ] = "planning_summary"
    format: Literal["csv", "xlsx"] = "csv"
    plant_code: str | None = None
    material_code: str | None = None
    criticality_status: str | None = None
    status: str | None = None


class ExportJobResponseSchema(BaseModel):
    export_id: str
    report_type: str
    format: str
    status: str
    created_at: str
    download_url: str


class ReportDatasetResponseSchema(BaseModel):
    title: str
    headers: list[str]
    rows: list[list[Any]]
    total_records: int
