from __future__ import annotations

import csv
import io
from typing import Any

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models.domain import Allocation, Material, Plant
from app.services.forecasting.engine import generate_demand_forecast
from app.services.planning.engine import evaluate_material_planning


class ReportingError(AppError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__("REPORTING_ERROR", message, status_code)


VALID_REPORT_TYPES = {
    "planning_summary",
    "inventory_planning",
    "forecast_summary",
    "demand_forecasting",
    "allocations",
    "vendor_allocations",
}
VALID_FORMATS = {"csv", "xlsx"}


def get_report_dataset(
    db: Session,
    report_type: str,
    plant_code: str | None = None,
    material_code: str | None = None,
    criticality_status: str | None = None,
    status: str | None = None,
) -> tuple[str, list[str], list[list[Any]]]:
    """Fetches report dataset using existing authoritative calculation services."""
    norm_type = report_type.lower()
    if norm_type not in VALID_REPORT_TYPES:
        msg = (
            f"Unsupported report type '{report_type}'. "
            "Valid types: planning_summary, forecast_summary, allocations."
        )
        raise ReportingError(msg)

    if norm_type in ("planning_summary", "inventory_planning"):
        return _get_planning_report(db, plant_code, material_code, criticality_status)
    elif norm_type in ("forecast_summary", "demand_forecasting"):
        return _get_forecast_report(db, plant_code, material_code)
    else:
        return _get_allocations_report(db, plant_code, material_code, status)


def _get_planning_report(
    db: Session,
    plant_code: str | None,
    material_code: str | None,
    criticality_status: str | None,
) -> tuple[str, list[str], list[list[Any]]]:
    title = "Planning Summary"
    headers = [
        "Plant Code",
        "Plant Name",
        "Material Code",
        "Material Description",
        "Base UOM",
        "Usable Stock",
        "Reserved Stock",
        "Blocked Stock",
        "Incoming PO Qty",
        "Committed Allocations",
        "Planning Availability",
        "Avg Daily Demand",
        "Demand Std Dev",
        "Lead Time Days",
        "Service Level Z",
        "ABC Class",
        "Safety Stock",
        "Demand During Lead Time",
        "Reorder Point",
        "Criticality Status",
        "Explanation",
    ]

    plants_query = db.query(Plant)
    if plant_code:
        plants_query = plants_query.filter(Plant.code == plant_code)
    plants = plants_query.all()

    materials_query = db.query(Material)
    if material_code:
        materials_query = materials_query.filter(Material.code == material_code)
    materials = materials_query.all()

    rows: list[list[Any]] = []
    for plant in plants:
        for mat in materials:
            try:
                res = evaluate_material_planning(
                    db=db, plant_code=plant.code, material_code=mat.code
                )
                if criticality_status and res.criticality_status != criticality_status.upper():
                    continue
                rows.append([
                    res.plant_code,
                    res.plant_name,
                    res.material_code,
                    res.material_description,
                    res.base_uom,
                    res.usable_physical_stock,
                    res.reserved_stock_info,
                    res.blocked_stock_info,
                    res.eligible_incoming_po_qty,
                    res.committed_allocations,
                    res.planning_availability,
                    res.average_daily_demand,
                    res.demand_std_dev,
                    res.lead_time_days,
                    res.service_level_z,
                    res.abc_class,
                    res.safety_stock,
                    res.demand_during_lead_time,
                    res.reorder_point,
                    res.criticality_status,
                    res.explanation,
                ])
            except Exception:
                continue

    return title, headers, rows


def _get_forecast_report(
    db: Session,
    plant_code: str | None,
    material_code: str | None,
) -> tuple[str, list[str], list[list[Any]]]:
    title = "Demand Forecast Summary"
    headers = [
        "Plant Code",
        "Material Code",
        "Base UOM",
        "Selected Model",
        "Evaluation Metric",
        "WMAPE Value",
        "Is Fallback",
        "Historical Window Days",
        "Forecast Horizon Days",
        "Total Forecasted Demand",
        "Avg Daily Forecast Demand",
    ]

    plants_query = db.query(Plant)
    if plant_code:
        plants_query = plants_query.filter(Plant.code == plant_code)
    plants = plants_query.all()

    materials_query = db.query(Material)
    if material_code:
        materials_query = materials_query.filter(Material.code == material_code)
    materials = materials_query.all()

    rows: list[list[Any]] = []
    for plant in plants:
        for mat in materials:
            try:
                res = generate_demand_forecast(
                    db=db, plant_code=plant.code, material_code=mat.code
                )
                rows.append([
                    res.plant_code,
                    res.material_code,
                    res.base_uom,
                    res.selected_model,
                    res.evaluation_metric_name,
                    res.evaluation_metric_value,
                    res.is_fallback,
                    res.historical_window_days,
                    res.forecast_horizon_days,
                    res.total_forecasted_demand,
                    res.average_forecasted_daily_demand,
                ])
            except Exception:
                continue

    return title, headers, rows


def _get_allocations_report(
    db: Session,
    plant_code: str | None,
    material_code: str | None,
    status: str | None,
) -> tuple[str, list[str], list[list[Any]]]:
    title = "Vendor Allocations"
    headers = [
        "Allocation Number",
        "Plant Code",
        "Plant Name",
        "Material Code",
        "Material Description",
        "Vendor Code",
        "Vendor Name",
        "Allocated Quantity",
        "UOM",
        "Status",
        "Created By",
        "Approved By",
        "Rejection Reason",
        "SAP Reference ID",
        "Version",
        "Created At",
    ]

    query = db.query(Allocation)
    if plant_code:
        query = query.filter(Allocation.plant.has(code=plant_code))
    if material_code:
        query = query.filter(Allocation.material.has(code=material_code))
    if status:
        query = query.filter(Allocation.status == status.upper())

    allocs = query.order_by(Allocation.id.desc()).all()
    rows: list[list[Any]] = []
    for a in allocs:
        rows.append([
            a.allocation_number,
            a.plant.code if a.plant else "",
            a.plant.name if a.plant else "",
            a.material.code if a.material else "",
            a.material.description if a.material else "",
            a.vendor.code if a.vendor else "",
            a.vendor.name if a.vendor else "",
            a.allocated_quantity,
            a.uom,
            a.status,
            a.created_by_user.email if a.created_by_user else "",
            a.approved_by_user.email if a.approved_by_user else "",
            a.rejection_reason or "",
            a.sap_reference_id or "",
            a.version,
            a.created_at.isoformat() if a.created_at else "",
        ])

    return title, headers, rows


def build_csv_export(headers: list[str], rows: list[list[Any]]) -> bytes:
    """Builds UTF-8 encoded CSV byte string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([str(val) if val is not None else "" for val in row])
    return output.getvalue().encode("utf-8")


def build_xlsx_export(sheet_title: str, headers: list[str], rows: list[list[Any]]) -> bytes:
    """Builds Excel (.xlsx) binary payload using openpyxl."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_title[:31]

    header_fill = PatternFill(start_color="1F2937", end_color="1F2937", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

    ws.append(headers)
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for row in rows:
        ws.append([str(val) if val is not None else "" for val in row])

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
