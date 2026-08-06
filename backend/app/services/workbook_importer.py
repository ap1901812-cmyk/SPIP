from __future__ import annotations

import io
import logging
import re
import time
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.errors import AppError

from app.db.models.domain import (
    BOM,
    Allocation,
    ConsumptionHistory,
    DailyIBPPlan,
    ForecastRecord,
    InventorySnapshot,
    Material,
    MaterialTypeEnum,
    MonthlyProductionPlan,
    PMOverride,
    PlanningExecutionRecord,
    Plant,
    PlantMaterial,
    ProcurementRecommendation,
    ProductionReadinessRecord,
    PurchaseOrder,
    PurchaseOrderLine,
    RMTotalityMapping,
    SimulationRun,
    VehicleMaster,
    Vendor,
    VendorCapacity,
    VendorMaterial,
)

try:
    import openpyxl
except ImportError:
    openpyxl = None


logger = logging.getLogger("spip.workbook_importer")


class WorkbookImportError(AppError):
    def __init__(
        self,
        message: str,
        workbook_name: str = "",
        sheet_name: str = "",
        row_number: Optional[int] = None,
        column_name: str = "",
        received_value: Any = None,
        expected_value: str = "",
        validation_rule: str = "",
        reason: str = "",
        details: Optional[Any] = None,
    ) -> None:
        if not details and (sheet_name or validation_rule or reason):
            details = {
                "workbook_name": workbook_name,
                "sheet_name": sheet_name,
                "row_number": row_number,
                "column_name": column_name,
                "received_value": str(received_value) if received_value is not None else "N/A",
                "expected_value": expected_value,
                "validation_rule": validation_rule,
                "reason": reason or message,
            }
        super().__init__("WORKBOOK_IMPORT_ERROR", message, 400, details=details)


def _raise_import_error(
    filename: str,
    sheet_name: str,
    row_number: Optional[int],
    column_name: str,
    received_value: Any,
    expected_value: str,
    validation_rule: str,
    reason: str,
    phase: str = "Validation",
    start_time: Optional[float] = None,
) -> None:
    exec_time = round((time.perf_counter() - start_time) * 1000.0, 2) if start_time else 0.0
    logger.error(
        f"[WORKBOOK_IMPORT_TRACE] FAILED\n"
        f"Phase: {phase}\n"
        f"Sheet: {sheet_name}\n"
        f"Row: {row_number or 'N/A'}\n"
        f"Column: {column_name}\n"
        f"Reason: {reason}\n"
        f"Execution Time: {exec_time} ms"
    )
    raise WorkbookImportError(
        message=f"{sheet_name} (Row {row_number or 'N/A'}, Column '{column_name}'): {reason}",
        workbook_name=filename,
        sheet_name=sheet_name,
        row_number=row_number,
        column_name=column_name,
        received_value=received_value,
        expected_value=expected_value,
        validation_rule=validation_rule,
        reason=reason,
    )



class SheetHeaderMapping(BaseModel):
    raw_header: str
    mapped_field: str


class SheetImportSummary(BaseModel):
    sheet_name: str
    imported: int = 0
    updated: int = 0
    rejected: int = 0
    warnings: list[str] = []
    header_mappings: list[SheetHeaderMapping] = []


class WorkbookImportReport(BaseModel):
    success: bool
    workbook_name: str
    workbook_type: str
    total_imported: int
    total_updated: int
    total_rejected: int
    execution_time_ms: float
    sheets_summary: list[SheetImportSummary]
    errors: list[str] = []


# --------------------------------------------------------------------------
# INTELLIGENT ENTERPRISE HEADER MAPPING & ALIAS DICTIONARY
# --------------------------------------------------------------------------

def _normalize_header(h: str) -> str:
    """Ignore case, spaces, underscores, hyphens, camelCase vs snake_case."""
    if not h:
        return ""
    # Convert camelCase to snake_case style boundary before stripping
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(h)).lower()
    # Strip all non-alphanumeric characters
    return re.sub(r"[^a-z0-9]", "", s)


def _normalize_sheet_name(name: str) -> str:
    if not name:
        return ""
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(name)).lower()
    norm = re.sub(r"[^a-z0-9]", "", s)

    if "purchaseorderline" in norm or "polines" in norm:
        return "purchase_order_lines"
    if "purchaseorder" in norm or "poheader" in norm:
        return "purchase_orders"
    if "consumption" in norm:
        return "consumption_history"
    if "inventory" in norm or "stock" in norm:
        return "inventory_snapshot"
    if "monthlyproduction" in norm or "productionplan" in norm:
        return "monthly_production_plan"
    if "ibp" in norm or "dailyibp" in norm:
        return "daily_ibp_plan"
    if "plantmaster" in norm:
        return "plant_master"
    if "materialmaster" in norm:
        return "material_master"
    if "vendormaterial" in norm:
        return "vendor_material_mapping"
    if "vendormaster" in norm:
        return "vendor_master"
    if "vehicle" in norm or "truck" in norm:
        return "vehicle_master"
    if "rmtotality" in norm or "totality" in norm:
        return "rm_totality_mapping"
    if "pmoverride" in norm:
        return "pm_overrides"
    if "pmmapping" in norm or "bom" in norm:
        return "pm_mapping"
    return norm


# --------------------------------------------------------------------------
# ENTERPRISE SHEET-AWARE HEADER ALIAS DICTIONARY
# Generic terms (Quantity, Name, Code, Description, Type) are NEVER resolved globally.
# --------------------------------------------------------------------------

SHEET_HEADER_ALIASES: dict[str, dict[str, list[str]]] = {
    "plant_master": {
        "plant_code": [
            "plant_code", "plant_id", "plant", "plantcode", "plantid",
            "plant-code", "plant-id", "factory_code", "location_code", "site_code", "code"
        ],
        "plant_name": [
            "plant_name", "plantname", "plant_description", "name", "factory_name", "site_name", "description"
        ],
        "location": [
            "location", "address", "city", "site_location"
        ],
        "storage_capacity_tons": [
            "storage_capacity_tons", "storage_capacity", "warehouse_capacity", "storage_cap",
            "capacity_tons", "max_storage_tons", "storage_cap_tons", "capacity"
        ],
        "is_active": [
            "is_active", "active", "status"
        ],
    },
    "material_master": {
        "material_code": [
            "material_code", "material_id", "item_code", "item_id", "material", "materialcode",
            "materialid", "itemcode", "sku", "sku_code", "part_number", "code"
        ],
        "material_name": [
            "material_name", "material_description", "description", "item_name", "material_desc", "name"
        ],
        "material_type": [
            "material_type", "type", "mat_type", "item_type", "category"
        ],
        "uom": [
            "uom", "base_uom", "unit", "unit_of_measure", "unit_of_measurement"
        ],
        "lead_time_1_days": [
            "lead_time_1_days", "lead_time_1", "lead_time", "lead_time_days", "procurement_lead_time", "lt_days", "lt1"
        ],
        "lead_time_2_days": [
            "lead_time_2_days", "lead_time_2", "lt2", "secondary_lead_time"
        ],
        "safety_stock_1_qty": [
            "safety_stock_1_qty", "safety_stock_1", "safety_stock", "ss1", "target_safety_stock"
        ],
        "safety_stock_2_qty": [
            "safety_stock_2_qty", "safety_stock_2", "ss2"
        ],
        "abc_classification": [
            "abc_classification", "abc_category", "abc_class", "abc"
        ],
    },
    "vendor_master": {
        "vendor_code": [
            "vendor_code", "vendor_id", "supplier_code", "supplier_id", "vendor", "supplier", "vendorcode", "vendorid", "code"
        ],
        "vendor_name": [
            "vendor_name", "supplier_name", "vendor_desc", "name", "description"
        ],
        "contact_email": [
            "contact_email", "email", "supplier_email", "contact"
        ],
        "capacity_tons_per_month": [
            "capacity_tons_per_month", "capacity_per_day", "vendor_capacity", "capacity_tons", "capacity", "monthly_capacity"
        ],
        "is_active": [
            "is_active", "active", "status"
        ],
    },
    "vendor_material_mapping": {
        "vendor_code": [
            "vendor_code", "vendor_id", "supplier_code", "supplier_id", "vendor", "supplier", "vendorcode", "vendorid"
        ],
        "material_code": [
            "material_code", "material_id", "item_code", "item_id", "material", "materialcode", "materialid", "itemcode", "sku", "sku_code", "part_number"
        ],
        "is_primary": [
            "is_primary", "primary_vendor", "primary", "preferred_vendor"
        ],
        "min_order_qty": [
            "min_order_qty", "moq", "minimum_order_qty", "min_order_quantity", "order_multiple"
        ],
    },
    "vehicle_master": {
        "vehicle_type_code": [
            "vehicle_type_code", "vehicle_code", "vehicle_id", "truck_type_code", "vehicle_type", "code", "type"
        ],
        "vehicle_type_name": [
            "vehicle_type_name", "vehicle_name", "truck_type_name", "vehicle_description", "name", "description"
        ],
        "storage_capacity_tons": [
            "capacity_tons", "vehicle_capacity", "truck_capacity", "load_capacity", "capacity", "max_capacity_tons", "storage_capacity_tons"
        ],
        "capacity_cbm": [
            "capacity_cbm", "cbm_capacity", "volume_cbm", "cbm"
        ],
        "cost_per_km": [
            "cost_per_km", "rate_per_km", "freight_cost_per_km", "cost_km"
        ],
    },
    "inventory_snapshot": {
        "plant_code": [
            "plant_code", "plant_id", "plant", "plantcode", "plantid", "factory_code", "site_code"
        ],
        "material_code": [
            "material_code", "material_id", "item_code", "item_id", "material", "materialcode", "materialid", "sku"
        ],
        "current_stock_qty": [
            "current_stock_qty", "inventory_qty", "available_stock", "usable_stock", "usable_physical_stock", "stock", "on_hand_qty", "quantity", "qty", "current_stock"
        ],
        "reserved_stock_qty": [
            "reserved_stock_qty", "reserved_stock", "reserved_qty", "safety_stock_reserved"
        ],
        "snapshot_date": [
            "snapshot_date", "date", "as_of_date", "inventory_date", "posting_date"
        ],
    },
    "consumption_history": {
        "plant_code": [
            "plant_code", "plant_id", "plant", "plantcode", "plantid", "factory_code", "site_code"
        ],
        "material_code": [
            "material_code", "material_id", "item_code", "item_id", "material", "materialcode", "materialid", "sku"
        ],
        "posting_date": [
            "posting_date", "date", "consumption_date", "usage_date", "transaction_date"
        ],
        "quantity_consumed": [
            "quantity_consumed", "consumption", "consumed_qty", "quantity", "actual_consumption", "usage_qty", "qty"
        ],
    },
    "purchase_orders": {
        "po_number": [
            "po_number", "po", "po_num", "order_number", "purchase_order", "po_no", "po_id"
        ],
        "vendor_code": [
            "vendor_code", "vendor_id", "supplier_code", "supplier_id", "vendor", "supplier", "vendorcode", "vendorid"
        ],
        "plant_code": [
            "plant_code", "plant_id", "plant", "plantcode", "plantid", "factory_code", "site_code"
        ],
        "po_date": [
            "po_date", "order_date", "date", "creation_date"
        ],
        "expected_delivery_date": [
            "expected_delivery_date", "delivery_date", "due_date", "promised_date"
        ],
        "status": [
            "status", "po_status", "order_status", "state"
        ],
    },
    "purchase_order_lines": {
        "po_number": [
            "po_number", "po", "po_num", "order_number", "purchase_order", "po_no", "po_id"
        ],
        "plant_code": [
            "plant_code", "plant_id", "plant", "plantcode", "plantid", "factory_code", "site_code"
        ],
        "material_code": [
            "material_code", "material_id", "item_code", "item_id", "material", "materialcode", "materialid", "sku"
        ],
        "line_number": [
            "line_number", "line", "line_no", "po_line", "item_number"
        ],
        "ordered_qty": [
            "ordered_qty", "order_quantity", "po_quantity", "ordered_quantity", "quantity", "qty"
        ],
        "received_qty": [
            "received_qty", "delivered_quantity", "delivered_qty", "received_quantity", "open_quantity"
        ],
    },
    "monthly_production_plan": {
        "plant_code": [
            "plant_code", "plant_id", "plant", "plantcode", "plantid", "factory_code", "site_code"
        ],
        "material_code": [
            "material_code", "material_id", "item_code", "item_id", "material", "materialcode", "materialid", "sku"
        ],
        "year": [
            "year", "plan_year", "yr"
        ],
        "month": [
            "month", "plan_month", "mth", "period"
        ],
        "planned_production_qty": [
            "planned_production_qty", "planned_qty", "production_qty", "planned_production", "quantity", "qty"
        ],
    },
    "daily_ibp_plan": {
        "plant_code": [
            "plant_code", "plant_id", "plant", "plantcode", "plantid", "factory_code", "site_code"
        ],
        "material_code": [
            "material_code", "material_id", "item_code", "item_id", "material", "materialcode", "materialid", "sku"
        ],
        "plan_date": [
            "plan_date", "date", "ibp_date", "posting_date"
        ],
        "required_daily_qty": [
            "required_daily_qty",
            "required_daily_quantity",
            "daily_qty",
            "daily_quantity",
            "required_qty",
            "required_quantity",
            "daily_ibp_qty",
            "daily_ibp_quantity",
            "ibp_req_qty",
            "planned_daily_qty",
            "forecast_qty",
            "forecast_quantity",
            "quantity",
            "qty",
        ],
    },
    "rm_totality_mapping": {
        "rm_material_code": [
            "rm_material_code", "rm_material_id", "rm_code", "raw_material_code", "raw_material", "rm", "rm_item_code"
        ],
        "totality_group_code": [
            "totality_group_code", "totality_group", "fg_group_name", "totality_group_name", "group_code", "rm_group"
        ],
        "contribution_ratio": [
            "contribution_ratio", "consumption_factor", "consumption_ratio", "usage_factor", "ratio"
        ],
    },
    "pm_mapping": {
        "fg_material_code": [
            "fg_material_code", "fg_material_id", "fg_code", "finished_good_code", "fg_material", "fg", "fg_item_code"
        ],
        "pm_material_code": [
            "pm_material_code", "pm_material_id", "pm_code", "packaging_material_code", "packaging_material", "pm", "pm_item_code"
        ],
        "usage_qty_per_fg": [
            "usage_qty_per_fg", "consumption_factor", "required_quantity", "usage_qty", "pm_usage_ratio", "qty_per_fg", "quantity", "qty"
        ],
    },
    "pm_overrides": {
        "plant_code": [
            "plant_code", "plant_id", "plant", "plantcode", "plantid", "factory_code", "site_code"
        ],
        "pm_material_code": [
            "pm_material_code", "pm_material_id", "pm_code", "packaging_material_code", "packaging_material", "pm", "pm_item_code"
        ],
        "override_usage_qty": [
            "override_usage_qty", "override_ratio", "override_usage", "override_qty", "quantity", "qty"
        ],
    },
}

# Pre-compute sheet-specific lookup maps: normalized_sheet -> { normalized_alias -> target_field }
_SHEET_NORMALIZED_ALIAS_MAPS: dict[str, dict[str, str]] = {}
for _s_key, _f_map in SHEET_HEADER_ALIASES.items():
    _SHEET_NORMALIZED_ALIAS_MAPS[_s_key] = {}
    for target_field, aliases in _f_map.items():
        for alias in aliases:
            norm = _normalize_header(alias)
            if norm and norm not in _SHEET_NORMALIZED_ALIAS_MAPS[_s_key]:
                _SHEET_NORMALIZED_ALIAS_MAPS[_s_key][norm] = target_field

# Global flat compatibility map (excluding generic ambiguous aliases)
HEADER_ALIASES: dict[str, list[str]] = {}
for _s_key, _f_map in SHEET_HEADER_ALIASES.items():
    for target_field, aliases in _f_map.items():
        if target_field not in HEADER_ALIASES:
            HEADER_ALIASES[target_field] = []
        for a in aliases:
            if a not in HEADER_ALIASES[target_field]:
                HEADER_ALIASES[target_field].append(a)

GENERIC_AMBIGUOUS_ALIASES: set[str] = {"quantity", "qty", "name", "code", "description", "type", "date"}

_GLOBAL_NORMALIZED_ALIAS_MAP: dict[str, str] = {}
for target_field, aliases in HEADER_ALIASES.items():
    for alias in aliases:
        norm = _normalize_header(alias)
        if norm and norm not in GENERIC_AMBIGUOUS_ALIASES and norm not in _GLOBAL_NORMALIZED_ALIAS_MAP:
            _GLOBAL_NORMALIZED_ALIAS_MAP[norm] = target_field


def _map_header_to_field(raw_header: str, sheet_name: str = "") -> str:
    """Map raw Excel header to internal standard field using sheet-aware alias resolution."""
    norm_h = _normalize_header(raw_header)
    if not norm_h:
        return ""

    if sheet_name:
        s_key = _normalize_sheet_name(sheet_name)
        sheet_map = _SHEET_NORMALIZED_ALIAS_MAPS.get(s_key, {})
        if norm_h in sheet_map:
            return sheet_map[norm_h]

    # Global fallback if sheet_name not matched or header not in sheet map
    if norm_h in _GLOBAL_NORMALIZED_ALIAS_MAP:
        return _GLOBAL_NORMALIZED_ALIAS_MAP[norm_h]

    return raw_header.strip().lower()


def _normalize(val: Any) -> str:
    if val is None:
        return ""
    return str(val).strip()


def _parse_date_val(val: Any) -> date | None:
    if not val:
        return None
    if isinstance(val, (date, datetime)):
        return val.date() if isinstance(val, datetime) else val
    s = str(val).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def _parse_float(val: Any, default: float = 0.0) -> float:
    if val is None or val == "":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _parse_int(val: Any, default: int = 0) -> int:
    if val is None or val == "":
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def _parse_bool(val: Any, default: bool = True) -> bool:
    if val is None or val == "":
        return default
    s = str(val).strip().lower()
    return s in ("1", "true", "yes", "y", "active")


def _parse_period(row: dict[str, Any], default_year: Optional[int] = None, default_month: Optional[int] = None) -> tuple[int, int]:
    def_yr = default_year if default_year is not None else datetime.now().year
    def_mn = default_month if default_month is not None else datetime.now().month

    # Format 4: Check for direct datetime / date objects in period/month/year fields
    for field_key in ("month", "period", "year", "plan_date", "posting_date", "date"):
        val = row.get(field_key)
        if isinstance(val, (datetime, date)):
            return val.year, val.month

    # Check for combined string formats in period or month fields (e.g. 2026-08, 2026/09, 08-2026)
    period_val = row.get("period") or row.get("month") or row.get("year")
    if period_val is not None and not isinstance(period_val, (dict, list)):
        p_str = str(period_val).strip()
        # Format 2 & 3: Match YYYY-MM, YYYY/MM, YYYY.MM
        m = re.match(r"^(\d{4})[-/\.](\d{1,2})(?:[-/\.]\d{1,2})?", p_str)
        if m:
            yr = int(m.group(1))
            mn = int(m.group(2))
            if 1 <= mn <= 12:
                return yr, mn

        # Match MM-YYYY, MM/YYYY
        m_rev = re.match(r"^(\d{1,2})[-/\.](\d{4})", p_str)
        if m_rev:
            mn = int(m_rev.group(1))
            yr = int(m_rev.group(2))
            if 1 <= mn <= 12:
                return yr, mn

    # Format 1: Separate Year and Month columns
    raw_yr = row.get("year")
    raw_mn = row.get("month")

    yr = _parse_int(raw_yr, def_yr) if raw_yr is not None and raw_yr != "" else def_yr
    mn = _parse_int(raw_mn, def_mn) if raw_mn is not None and raw_mn != "" else def_mn

    if mn < 1 or mn > 12:
        mn = def_mn

    return yr, mn


def clear_business_data(db: Session) -> None:
    """Clear all business transactional and master data tables while retaining auth & system metadata."""
    tables_in_order = [
        "allocations",
        "procurement_recommendations",
        "production_readiness_records",
        "planning_execution_records",
        "simulation_runs",
        "forecast_records",
        "pm_overrides",
        "rm_totality_mappings",
        "daily_ibp_plans",
        "monthly_production_plans",
        "purchase_order_lines",
        "purchase_orders",
        "consumption_history",
        "inventory_snapshots",
        "vendor_materials",
        "vehicle_masters",
        "vendors",
        "boms",
        "plant_materials",
        "materials",
        "plants",
    ]
    for table in tables_in_order:
        db.execute(text(f"DELETE FROM {table}"))
    db.flush()


def import_enterprise_workbook(
    db: Session,
    file_bytes: bytes,
    filename: str = "workbook.xlsx",
    replace_existing: bool = False,
) -> WorkbookImportReport:
    start_t = time.perf_counter()

    if openpyxl is None:
        _raise_import_error(
            filename=filename,
            sheet_name="N/A",
            row_number=None,
            column_name="N/A",
            received_value=None,
            expected_value="openpyxl installed",
            validation_rule="Dependency Check",
            reason="openpyxl is not installed on backend.",
            phase="Workbook Parsing",
            start_time=start_t,
        )

    logger.info(f"[WORKBOOK_IMPORT_TRACE] Workbook detected: {filename}")

    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    except Exception as e:
        _raise_import_error(
            filename=filename,
            sheet_name="N/A",
            row_number=None,
            column_name="N/A",
            received_value=None,
            expected_value="Valid Excel Workbook File (.xlsx)",
            validation_rule="Excel File Format",
            reason=f"Failed to parse Excel workbook file: {e}",
            phase="Workbook Parsing",
            start_time=start_t,
        )

    sheet_names = wb.sheetnames
    visible_sheets = [s for s in sheet_names if not wb[s].sheet_state == "hidden"]

    # Detect Workbook Type via sheet names
    has_wb1 = any(s in visible_sheets for s in ["Plant_Master", "Material_Master", "Vendor_Master"])
    has_wb2 = any(s in visible_sheets for s in ["Inventory_Snapshot", "Consumption_History", "Purchase_Orders"])
    has_wb3 = any(s in visible_sheets for s in ["RM_Totality_Mapping", "PM_Mapping", "PM_Overrides"])

    if has_wb1:
        workbook_type = "Workbook 1: Master Data"
        mandatory_sheets = ["Plant_Master", "Material_Master", "Vendor_Master", "Vendor_Material_Mapping", "Vehicle_Master"]
    elif has_wb2:
        workbook_type = "Workbook 2: Planning Data"
        mandatory_sheets = ["Inventory_Snapshot", "Consumption_History", "Purchase_Orders", "Purchase_Order_Lines", "Monthly_Production_Plan", "Daily_IBP_Plan"]
    elif has_wb3:
        workbook_type = "Workbook 3: SPIP Configuration"
        mandatory_sheets = ["RM_Totality_Mapping", "PM_Mapping", "PM_Overrides"]
    else:
        _raise_import_error(
            filename=filename,
            sheet_name="N/A",
            row_number=None,
            column_name="N/A",
            received_value=", ".join(visible_sheets),
            expected_value="Standard SPIP Workbook Sheet Structure",
            validation_rule="Workbook Structure Rule",
            reason=f"Unknown mandatory workbook structure. Visible sheets: {', '.join(visible_sheets)}",
            phase="Structure Detection",
            start_time=start_t,
        )

    logger.info(f"[WORKBOOK_IMPORT_TRACE] Detected {workbook_type}")

    # Verify mandatory sheets present
    for ms in mandatory_sheets:
        if ms not in visible_sheets:
            _raise_import_error(
                filename=filename,
                sheet_name=ms,
                row_number=None,
                column_name="N/A",
                received_value="Missing",
                expected_value=f"Mandatory sheet '{ms}' present",
                validation_rule="Mandatory Sheet Constraint",
                reason=f"Missing mandatory sheet '{ms}' for {workbook_type}",
                phase="Sheet Structure Validation",
                start_time=start_t,
            )

    sheets_summary: list[SheetImportSummary] = []
    total_imported = 0
    total_updated = 0
    total_rejected = 0

    savepoint = db.begin_nested()
    try:
        if replace_existing:
            logger.info(f"[WORKBOOK_IMPORT_TRACE] Replacing existing business data for {workbook_type}")
            clear_business_data(db)

        if workbook_type == "Workbook 1: Master Data":
            logger.info("[WORKBOOK_IMPORT_TRACE] Parsing Plant_Master")
            s1 = _import_plant_master(db, wb["Plant_Master"], filename, start_t)
            logger.info(f"[WORKBOOK_IMPORT_TRACE] Imported {s1.imported} records (Updated {s1.updated})")
            sheets_summary.append(s1)

            logger.info("[WORKBOOK_IMPORT_TRACE] Parsing Material_Master")
            s2 = _import_material_master(db, wb["Material_Master"], filename, start_t)
            logger.info(f"[WORKBOOK_IMPORT_TRACE] Imported {s2.imported} records (Updated {s2.updated})")
            sheets_summary.append(s2)

            logger.info("[WORKBOOK_IMPORT_TRACE] Parsing Vendor_Master")
            s3 = _import_vendor_master(db, wb["Vendor_Master"], filename, start_t)
            logger.info(f"[WORKBOOK_IMPORT_TRACE] Imported {s3.imported} records (Updated {s3.updated})")
            sheets_summary.append(s3)

            logger.info("[WORKBOOK_IMPORT_TRACE] Parsing Vendor_Material_Mapping")
            s4 = _import_vendor_material_mapping(db, wb["Vendor_Material_Mapping"], filename, start_t)
            logger.info(f"[WORKBOOK_IMPORT_TRACE] Imported {s4.imported} records (Updated {s4.updated})")
            sheets_summary.append(s4)

            logger.info("[WORKBOOK_IMPORT_TRACE] Parsing Vehicle_Master")
            s5 = _import_vehicle_master(db, wb["Vehicle_Master"], filename, start_t)
            logger.info(f"[WORKBOOK_IMPORT_TRACE] Imported {s5.imported} records (Updated {s5.updated})")
            sheets_summary.append(s5)

        elif workbook_type == "Workbook 2: Planning Data":
            logger.info("[WORKBOOK_IMPORT_TRACE] Parsing Inventory_Snapshot")
            s1 = _import_inventory_snapshot(db, wb["Inventory_Snapshot"], filename, start_t)
            logger.info(f"[WORKBOOK_IMPORT_TRACE] Imported {s1.imported} records (Updated {s1.updated})")
            sheets_summary.append(s1)

            logger.info("[WORKBOOK_IMPORT_TRACE] Parsing Consumption_History")
            s2 = _import_consumption_history(db, wb["Consumption_History"], filename, start_t)
            logger.info(f"[WORKBOOK_IMPORT_TRACE] Imported {s2.imported} records (Updated {s2.updated})")
            sheets_summary.append(s2)

            logger.info("[WORKBOOK_IMPORT_TRACE] Parsing Purchase_Orders")
            s3 = _import_purchase_orders(db, wb["Purchase_Orders"], filename, start_t)
            logger.info(f"[WORKBOOK_IMPORT_TRACE] Imported {s3.imported} records (Updated {s3.updated})")
            sheets_summary.append(s3)

            logger.info("[WORKBOOK_IMPORT_TRACE] Parsing Purchase_Order_Lines")
            s4 = _import_purchase_order_lines(db, wb["Purchase_Order_Lines"], filename, start_t)
            logger.info(f"[WORKBOOK_IMPORT_TRACE] Imported {s4.imported} records (Updated {s4.updated})")
            sheets_summary.append(s4)

            logger.info("[WORKBOOK_IMPORT_TRACE] Parsing Monthly_Production_Plan")
            s5 = _import_monthly_production_plan(db, wb["Monthly_Production_Plan"], filename, start_t)
            logger.info(f"[WORKBOOK_IMPORT_TRACE] Imported {s5.imported} records (Updated {s5.updated})")
            sheets_summary.append(s5)

            logger.info("[WORKBOOK_IMPORT_TRACE] Parsing Daily_IBP_Plan")
            s6 = _import_daily_ibp_plan(db, wb["Daily_IBP_Plan"], filename, start_t)
            logger.info(f"[WORKBOOK_IMPORT_TRACE] Imported {s6.imported} records (Updated {s6.updated})")
            sheets_summary.append(s6)

        elif workbook_type == "Workbook 3: SPIP Configuration":
            logger.info("[WORKBOOK_IMPORT_TRACE] Parsing RM_Totality_Mapping")
            s1 = _import_rm_totality_mapping(db, wb["RM_Totality_Mapping"], filename, start_t)
            logger.info(f"[WORKBOOK_IMPORT_TRACE] Imported {s1.imported} records (Updated {s1.updated})")
            sheets_summary.append(s1)

            logger.info("[WORKBOOK_IMPORT_TRACE] Parsing PM_Mapping")
            s2 = _import_pm_mapping(db, wb["PM_Mapping"], filename, start_t)
            logger.info(f"[WORKBOOK_IMPORT_TRACE] Imported {s2.imported} records (Updated {s2.updated})")
            sheets_summary.append(s2)

            logger.info("[WORKBOOK_IMPORT_TRACE] Parsing PM_Overrides")
            s3 = _import_pm_overrides(db, wb["PM_Overrides"], filename, start_t)
            logger.info(f"[WORKBOOK_IMPORT_TRACE] Imported {s3.imported} records (Updated {s3.updated})")
            sheets_summary.append(s3)

        logger.info("[WORKBOOK_IMPORT_TRACE] Foreign Key Validation Passed")
        logger.info("[WORKBOOK_IMPORT_TRACE] Business Rule Validation Passed")
        savepoint.commit()
        db.commit()
        logger.info("[WORKBOOK_IMPORT_TRACE] Database Commit - Import Completed")

    except Exception as err:
        savepoint.rollback()
        db.rollback()
        if isinstance(err, WorkbookImportError):
            raise err
        exec_t = round((time.perf_counter() - start_t) * 1000.0, 2)
        logger.error(f"[WORKBOOK_IMPORT_TRACE] FAILED\nPhase: Execution\nReason: {err}\nExecution Time: {exec_t} ms", exc_info=True)
        
        err_str = str(err)
        if "uq_monthly_prod_plan" in err_str or "monthly_production_plans" in err_str.lower():
            clean_reason = "Duplicate Monthly Production Plan entry detected for the same Plant, Material, Year, and Month."
            raise WorkbookImportError(
                message=clean_reason,
                workbook_name=filename,
                sheet_name="Monthly_Production_Plan",
                validation_rule="Unique Production Plan Constraint",
                reason=clean_reason,
            )
        elif "unique constraint" in err_str.lower() or "duplicate key" in err_str.lower():
            clean_reason = "Duplicate record detected violating database unique constraint."
            raise WorkbookImportError(
                message=clean_reason,
                workbook_name=filename,
                validation_rule="Unique Constraint Rule",
                reason=clean_reason,
            )

        raise WorkbookImportError(
            message=f"Workbook import failed & rolled back completely: {err}",
            workbook_name=filename,
            reason=str(err),
        )

    for s in sheets_summary:
        total_imported += s.imported
        total_updated += s.updated
        total_rejected += s.rejected

    elapsed_ms = round((time.perf_counter() - start_t) * 1000.0, 2)

    return WorkbookImportReport(
        success=True,
        workbook_name=filename,
        workbook_type=workbook_type,
        total_imported=total_imported,
        total_updated=total_updated,
        total_rejected=total_rejected,
        execution_time_ms=elapsed_ms,
        sheets_summary=sheets_summary,
    )



def _get_sheet_rows_and_mappings(ws: Any, sheet_name: str = "") -> tuple[list[dict[str, Any]], list[SheetHeaderMapping]]:
    eff_sheet_name = sheet_name or getattr(ws, "title", "")
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return [], []
    
    raw_headers = [str(cell).strip() if cell is not None else "" for cell in rows[0]]
    mapped_headers = []
    header_mappings = []

    for raw in raw_headers:
        if not raw:
            mapped_headers.append("")
            continue
        mapped_field = _map_header_to_field(raw, sheet_name=eff_sheet_name)
        mapped_headers.append(mapped_field)
        header_mappings.append(SheetHeaderMapping(raw_header=raw, mapped_field=mapped_field))

    data_rows = []
    for r in rows[1:]:
        if not any(r):
            continue
        row_dict = {}
        for idx, val in enumerate(r):
            if idx < len(mapped_headers) and mapped_headers[idx]:
                field_key = mapped_headers[idx]
                row_dict[field_key] = val
        data_rows.append(row_dict)

    return data_rows, header_mappings


def _raise_missing_field_error(
    sheet_name: str, field_name: str, filename: str = "workbook.xlsx", start_t: Optional[float] = None
) -> None:
    s_key = _normalize_sheet_name(sheet_name)
    sheet_map = SHEET_HEADER_ALIASES.get(s_key, {})
    aliases = sheet_map.get(field_name, HEADER_ALIASES.get(field_name, [field_name]))
    aliases_formatted = ", ".join(set(aliases[:4] + [field_name]))
    reason = f"Required field '{field_name}' was not found in header. Expected one of: {aliases_formatted}."
    _raise_import_error(
        filename=filename,
        sheet_name=sheet_name,
        row_number=1,
        column_name=field_name,
        received_value=None,
        expected_value=f"Header matching field '{field_name}'",
        validation_rule="Header Normalization Rule",
        reason=reason,
        phase="Header Normalization",
        start_time=start_t,
    )


# --------------------------------------------------------------------------
# WORKBOOK 1 PARSERS
# --------------------------------------------------------------------------

def _import_plant_master(
    db: Session, ws: Any, filename: str = "workbook.xlsx", start_t: Optional[float] = None
) -> SheetImportSummary:
    summary = SheetImportSummary(sheet_name="Plant_Master")
    rows, header_mappings = _get_sheet_rows_and_mappings(ws, "Plant_Master")
    summary.header_mappings = header_mappings

    for idx, row in enumerate(rows, start=2):
        code = _normalize(row.get("plant_code"))
        name = _normalize(row.get("plant_name"))
        location = _normalize(row.get("location")) or None
        cap = _parse_float(row.get("storage_capacity_tons"), 10000.0)
        is_act = _parse_bool(row.get("is_active"), True)

        if not code:
            _raise_missing_field_error("Plant_Master", "plant_code", filename, start_t)
        if not name:
            name = f"Plant {code}"

        if cap <= 0:
            _raise_import_error(
                filename=filename,
                sheet_name="Plant_Master",
                row_number=idx,
                column_name="storage_capacity_tons",
                received_value=cap,
                expected_value="Number > 0",
                validation_rule="Storage Capacity > 0",
                reason=f"Storage Capacity must be > 0 (got {cap}).",
                phase="Business Rule Validation",
                start_time=start_t,
            )

        existing = db.query(Plant).filter(Plant.code == code).first()
        if existing:
            existing.name = name
            existing.location = location
            existing.storage_capacity_tons = cap
            existing.is_active = is_act
            summary.updated += 1
        else:
            p = Plant(code=code, name=name, location=location, storage_capacity_tons=cap, is_active=is_act)
            db.add(p)
            summary.imported += 1
    db.flush()
    return summary



def _import_material_master(
    db: Session, ws: Any, filename: str = "workbook.xlsx", start_t: Optional[float] = None
) -> SheetImportSummary:
    summary = SheetImportSummary(sheet_name="Material_Master")
    rows, header_mappings = _get_sheet_rows_and_mappings(ws, "Material_Master")
    summary.header_mappings = header_mappings
    plants = db.query(Plant).all()

    for idx, row in enumerate(rows, start=2):
        code = _normalize(row.get("material_code"))
        desc = _normalize(row.get("material_name") or row.get("material_description"))
        m_type_raw = _normalize(row.get("material_type")).upper()
        
        if not code:
            _raise_missing_field_error("Material_Master", "material_code", filename, start_t)
        if not desc:
            desc = code
        if not m_type_raw:
            _raise_missing_field_error("Material_Master", "material_type", filename, start_t)

        if m_type_raw not in ("RM", "PM", "FG"):
            _raise_import_error(
                filename=filename,
                sheet_name="Material_Master",
                row_number=idx,
                column_name="material_type",
                received_value=m_type_raw,
                expected_value="One of RM, PM, FG",
                validation_rule="Material Type Allowed Values",
                reason=f"Material type must be RM, PM, or FG (got '{m_type_raw}').",
                phase="Business Rule Validation",
                start_time=start_t,
            )
            
        m_type = MaterialTypeEnum.normalize(m_type_raw)
        uom = _normalize(row.get("uom")) or "KG"

        lt1 = _parse_float(row.get("lead_time_1_days"), 14.0)
        lt2 = _parse_float(row.get("lead_time_2_days"), 7.0)
        ss1 = _parse_float(row.get("safety_stock_1_qty"), 100.0)
        ss2 = _parse_float(row.get("safety_stock_2_qty"), 50.0)
        abc = _normalize(row.get("abc_classification") or row.get("abc_class") or "B") or "B"

        if m_type_raw in ("RM", "PM") and (lt1 <= 0 or lt2 <= 0):
            _raise_import_error(
                filename=filename,
                sheet_name="Material_Master",
                row_number=idx,
                column_name="lead_time_1_days / lead_time_2_days",
                received_value=f"lt1={lt1}, lt2={lt2}",
                expected_value="Number > 0 for RM/PM",
                validation_rule="Lead Time > 0",
                reason=f"Lead Time must be > 0 (got lt1={lt1}, lt2={lt2}).",
                phase="Business Rule Validation",
                start_time=start_t,
            )
        elif lt1 < 0 or lt2 < 0:
            _raise_import_error(
                filename=filename,
                sheet_name="Material_Master",
                row_number=idx,
                column_name="lead_time_1_days / lead_time_2_days",
                received_value=f"lt1={lt1}, lt2={lt2}",
                expected_value="Number >= 0",
                validation_rule="Lead Time >= 0",
                reason=f"Lead Time must be >= 0 (got lt1={lt1}, lt2={lt2}).",
                phase="Business Rule Validation",
                start_time=start_t,
            )

        mat = db.query(Material).filter(Material.code == code).first()
        if mat:
            mat.description = desc
            mat.material_type = m_type
            mat.base_uom = uom
            summary.updated += 1
        else:
            mat = Material(code=code, description=desc, material_type=m_type, base_uom=uom)
            db.add(mat)
            db.flush()
            summary.imported += 1

        for plant in plants:
            pm = db.query(PlantMaterial).filter(PlantMaterial.plant_id == plant.id, PlantMaterial.material_id == mat.id).first()
            if not pm:
                pm = PlantMaterial(
                    plant_id=plant.id,
                    material_id=mat.id,
                    lead_time_1=lt1,
                    lead_time_2=lt2,
                    safety_stock_1=ss1,
                    safety_stock_2=ss2,
                    abc_class=abc,
                )
                db.add(pm)
            else:
                pm.lead_time_1 = lt1
                pm.lead_time_2 = lt2
                pm.safety_stock_1 = ss1
                pm.safety_stock_2 = ss2
                pm.abc_class = abc

    db.flush()
    return summary


def _import_vendor_master(
    db: Session, ws: Any, filename: str = "workbook.xlsx", start_t: Optional[float] = None
) -> SheetImportSummary:
    summary = SheetImportSummary(sheet_name="Vendor_Master")
    rows, header_mappings = _get_sheet_rows_and_mappings(ws, "Vendor_Master")
    summary.header_mappings = header_mappings

    for idx, row in enumerate(rows, start=2):
        code = _normalize(row.get("vendor_code"))
        name = _normalize(row.get("vendor_name"))
        email = _normalize(row.get("contact_email")) or None
        cap = _parse_float(row.get("capacity_tons_per_month"), 500.0)
        is_act = _parse_bool(row.get("is_active"), True)

        if not code:
            _raise_missing_field_error("Vendor_Master", "vendor_code", filename, start_t)
        if not name:
            name = f"Vendor {code}"

        if cap < 0:
            _raise_import_error(
                filename=filename,
                sheet_name="Vendor_Master",
                row_number=idx,
                column_name="capacity_tons_per_month",
                received_value=cap,
                expected_value="Number >= 0",
                validation_rule="Vendor Capacity >= 0",
                reason=f"Vendor Capacity must be >= 0 (got {cap}).",
                phase="Business Rule Validation",
                start_time=start_t,
            )

        existing = db.query(Vendor).filter(Vendor.code == code).first()
        if existing:
            existing.name = name
            existing.contact_email = email
            existing.capacity_per_day = cap
            existing.is_active = is_act
            summary.updated += 1
        else:
            v = Vendor(code=code, name=name, contact_email=email, capacity_per_day=cap, is_active=is_act)
            db.add(v)
            summary.imported += 1

    db.flush()
    return summary


def _import_vendor_material_mapping(
    db: Session, ws: Any, filename: str = "workbook.xlsx", start_t: Optional[float] = None
) -> SheetImportSummary:
    summary = SheetImportSummary(sheet_name="Vendor_Material_Mapping")
    rows, header_mappings = _get_sheet_rows_and_mappings(ws, "Vendor_Material_Mapping")
    summary.header_mappings = header_mappings

    for idx, row in enumerate(rows, start=2):
        v_code = _normalize(row.get("vendor_code"))
        m_code = _normalize(row.get("material_code"))
        is_prim = _parse_bool(row.get("is_primary"), True)
        min_qty = _parse_float(row.get("min_order_qty"), 0.0)

        if not v_code:
            _raise_missing_field_error("Vendor_Material_Mapping", "vendor_code", filename, start_t)
        if not m_code:
            _raise_missing_field_error("Vendor_Material_Mapping", "material_code", filename, start_t)

        vendor = db.query(Vendor).filter(Vendor.code == v_code).first()
        material = db.query(Material).filter(Material.code == m_code).first()

        if not vendor:
            _raise_import_error(
                filename=filename,
                sheet_name="Vendor_Material_Mapping",
                row_number=idx,
                column_name="vendor_code",
                received_value=v_code,
                expected_value="Existing Vendor Master Code",
                validation_rule="Foreign Key Constraint",
                reason=f"Vendor '{v_code}' does not exist in Vendor_Master.",
                phase="Foreign Key Validation",
                start_time=start_t,
            )
        if not material:
            _raise_import_error(
                filename=filename,
                sheet_name="Vendor_Material_Mapping",
                row_number=idx,
                column_name="material_code",
                received_value=m_code,
                expected_value="Existing Material Master Code",
                validation_rule="Foreign Key Constraint",
                reason=f"Material '{m_code}' does not exist in Material_Master.",
                phase="Foreign Key Validation",
                start_time=start_t,
            )

        existing = db.query(VendorMaterial).filter(
            VendorMaterial.vendor_id == vendor.id,
            VendorMaterial.material_id == material.id,
        ).first()

        if existing:
            existing.is_primary = is_prim
            existing.min_order_qty = min_qty
            summary.updated += 1
        else:
            vm = VendorMaterial(
                vendor_id=vendor.id,
                material_id=material.id,
                is_primary=is_prim,
                min_order_qty=min_qty,
            )
            db.add(vm)
            summary.imported += 1

    db.flush()
    return summary


def _import_vehicle_master(
    db: Session, ws: Any, filename: str = "workbook.xlsx", start_t: Optional[float] = None
) -> SheetImportSummary:
    summary = SheetImportSummary(sheet_name="Vehicle_Master")
    rows, header_mappings = _get_sheet_rows_and_mappings(ws, "Vehicle_Master")
    summary.header_mappings = header_mappings

    for idx, row in enumerate(rows, start=2):
        code = _normalize(row.get("vehicle_type_code"))
        name = _normalize(row.get("vehicle_type_name"))
        tons = _parse_float(row.get("capacity_tons"), 25.0)
        cbm = _parse_float(row.get("capacity_cbm"), 50.0)
        cost = _parse_float(row.get("cost_per_km"), 15.0)

        if not code:
            _raise_missing_field_error("Vehicle_Master", "vehicle_type_code", filename, start_t)
        if not name:
            name = f"Vehicle {code}"

        if tons <= 0:
            _raise_import_error(
                filename=filename,
                sheet_name="Vehicle_Master",
                row_number=idx,
                column_name="capacity_tons",
                received_value=tons,
                expected_value="Number > 0",
                validation_rule="Vehicle Capacity > 0",
                reason=f"Vehicle Capacity must be > 0 (got {tons}).",
                phase="Business Rule Validation",
                start_time=start_t,
            )

        existing = db.query(VehicleMaster).filter(VehicleMaster.vehicle_type_code == code).first()
        if existing:
            existing.vehicle_type_name = name
            existing.capacity_tons = tons
            existing.capacity_cbm = cbm
            existing.cost_per_km = cost
            summary.updated += 1
        else:
            vm = VehicleMaster(
                vehicle_type_code=code,
                vehicle_type_name=name,
                capacity_tons=tons,
                capacity_cbm=cbm,
                cost_per_km=cost,
            )
            db.add(vm)
            summary.imported += 1

    db.flush()
    return summary



# --------------------------------------------------------------------------
# WORKBOOK 2 PARSERS
# --------------------------------------------------------------------------

def _import_inventory_snapshot(
    db: Session, ws: Any, filename: str = "workbook.xlsx", start_t: Optional[float] = None
) -> SheetImportSummary:
    summary = SheetImportSummary(sheet_name="Inventory_Snapshot")
    rows, header_mappings = _get_sheet_rows_and_mappings(ws, "Inventory_Snapshot")
    summary.header_mappings = header_mappings

    for idx, row in enumerate(rows, start=2):
        p_code = _normalize(row.get("plant_code"))
        m_code = _normalize(row.get("material_code"))
        stock = _parse_float(row.get("current_stock_qty"), 0.0)
        reserved = _parse_float(row.get("reserved_stock_qty"), 0.0)
        s_date = _parse_date_val(row.get("snapshot_date")) or date.today()

        if not p_code:
            _raise_missing_field_error("Inventory_Snapshot", "plant_code", filename, start_t)
        if not m_code:
            _raise_missing_field_error("Inventory_Snapshot", "material_code", filename, start_t)

        if stock < 0:
            _raise_import_error(
                filename=filename,
                sheet_name="Inventory_Snapshot",
                row_number=idx,
                column_name="current_stock_qty",
                received_value=stock,
                expected_value="Number >= 0",
                validation_rule="Stock Quantity >= 0",
                reason=f"Inventory quantity must be >= 0 (got {stock}).",
                phase="Business Rule Validation",
                start_time=start_t,
            )

        plant = db.query(Plant).filter(Plant.code == p_code).first()
        material = db.query(Material).filter(Material.code == m_code).first()

        if not plant:
            _raise_import_error(
                filename=filename,
                sheet_name="Inventory_Snapshot",
                row_number=idx,
                column_name="plant_code",
                received_value=p_code,
                expected_value="Existing Plant Master Code",
                validation_rule="Foreign Key Constraint",
                reason=f"Plant '{p_code}' does not exist in Plant_Master.",
                phase="Foreign Key Validation",
                start_time=start_t,
            )
        if not material:
            _raise_import_error(
                filename=filename,
                sheet_name="Inventory_Snapshot",
                row_number=idx,
                column_name="material_code",
                received_value=m_code,
                expected_value="Existing Material Master Code",
                validation_rule="Foreign Key Constraint",
                reason=f"Material '{m_code}' does not exist in Material_Master.",
                phase="Foreign Key Validation",
                start_time=start_t,
            )

        snap = InventorySnapshot(
            plant_id=plant.id,
            material_id=material.id,
            snapshot_date=s_date,
            usable_physical_stock=stock,
            reserved_stock=reserved,
            source="WORKBOOK_UAT",
        )
        db.add(snap)

        summary.imported += 1

    db.flush()
    return summary


def _import_consumption_history(
    db: Session, ws: Any, filename: str = "workbook.xlsx", start_t: Optional[float] = None
) -> SheetImportSummary:
    summary = SheetImportSummary(sheet_name="Consumption_History")
    rows, header_mappings = _get_sheet_rows_and_mappings(ws, "Consumption_History")
    summary.header_mappings = header_mappings

    for idx, row in enumerate(rows, start=2):
        p_code = _normalize(row.get("plant_code"))
        m_code = _normalize(row.get("material_code"))
        c_date = _parse_date_val(row.get("posting_date")) or date.today()
        qty = _parse_float(row.get("quantity_consumed"), 0.0)

        if not p_code:
            _raise_missing_field_error("Consumption_History", "plant_code", filename, start_t)
        if not m_code:
            _raise_missing_field_error("Consumption_History", "material_code", filename, start_t)

        if qty < 0:
            _raise_import_error(
                filename=filename,
                sheet_name="Consumption_History",
                row_number=idx,
                column_name="quantity_consumed",
                received_value=qty,
                expected_value="Number >= 0",
                validation_rule="Consumption Quantity >= 0",
                reason=f"Consumption quantity must be >= 0 (got {qty}).",
                phase="Business Rule Validation",
                start_time=start_t,
            )

        plant = db.query(Plant).filter(Plant.code == p_code).first()
        material = db.query(Material).filter(Material.code == m_code).first()

        if not plant:
            _raise_import_error(
                filename=filename,
                sheet_name="Consumption_History",
                row_number=idx,
                column_name="plant_code",
                received_value=p_code,
                expected_value="Existing Plant Master Code",
                validation_rule="Foreign Key Constraint",
                reason=f"Plant '{p_code}' does not exist in Plant_Master.",
                phase="Foreign Key Validation",
                start_time=start_t,
            )
        if not material:
            _raise_import_error(
                filename=filename,
                sheet_name="Consumption_History",
                row_number=idx,
                column_name="material_code",
                received_value=m_code,
                expected_value="Existing Material Master Code",
                validation_rule="Foreign Key Constraint",
                reason=f"Material '{m_code}' does not exist in Material_Master.",
                phase="Foreign Key Validation",
                start_time=start_t,
            )

        ch = ConsumptionHistory(
            plant_id=plant.id,
            material_id=material.id,
            consumption_date=c_date,
            quantity=qty,
            uom=material.base_uom or "KG",
            source="WORKBOOK_UAT",
        )
        db.add(ch)
        summary.imported += 1

    db.flush()
    return summary


def _import_purchase_orders(
    db: Session, ws: Any, filename: str = "workbook.xlsx", start_t: Optional[float] = None
) -> SheetImportSummary:
    summary = SheetImportSummary(sheet_name="Purchase_Orders")
    rows, header_mappings = _get_sheet_rows_and_mappings(ws, "Purchase_Orders")
    summary.header_mappings = header_mappings

    for idx, row in enumerate(rows, start=2):
        po_num = _normalize(row.get("po_number"))
        v_code = _normalize(row.get("vendor_code"))
        p_code = _normalize(row.get("plant_code"))
        po_d = _parse_date_val(row.get("po_date")) or date.today()
        exp_d = _parse_date_val(row.get("expected_delivery_date")) or date.today()
        st = _normalize(row.get("status") or "OPEN").upper() or "OPEN"

        if not po_num:
            _raise_missing_field_error("Purchase_Orders", "po_number", filename, start_t)
        if not v_code:
            _raise_missing_field_error("Purchase_Orders", "vendor_code", filename, start_t)

        plant = db.query(Plant).filter(Plant.code == p_code).first() if p_code else None
        vendor = db.query(Vendor).filter(Vendor.code == v_code).first()

        if p_code and not plant:
            _raise_import_error(
                filename=filename,
                sheet_name="Purchase_Orders",
                row_number=idx,
                column_name="plant_code",
                received_value=p_code,
                expected_value="Existing Plant Master Code",
                validation_rule="Foreign Key Constraint",
                reason=f"Plant '{p_code}' does not exist in Plant_Master.",
                phase="Foreign Key Validation",
                start_time=start_t,
            )
        if not vendor:
            _raise_import_error(
                filename=filename,
                sheet_name="Purchase_Orders",
                row_number=idx,
                column_name="vendor_code",
                received_value=v_code,
                expected_value="Existing Vendor Master Code",
                validation_rule="Foreign Key Constraint",
                reason=f"Vendor '{v_code}' does not exist in Vendor_Master.",
                phase="Foreign Key Validation",
                start_time=start_t,
            )

        existing = db.query(PurchaseOrder).filter(PurchaseOrder.po_number == po_num).first()
        if existing:
            if plant:
                existing.plant_id = plant.id
            existing.vendor_id = vendor.id
            existing.po_date = po_d
            existing.expected_delivery_date = exp_d
            existing.status = st
            summary.updated += 1
        else:
            po = PurchaseOrder(
                po_number=po_num,
                plant_id=plant.id if plant else None,
                vendor_id=vendor.id,
                po_date=po_d,
                expected_delivery_date=exp_d,
                status=st,
            )
            db.add(po)
            summary.imported += 1

    db.flush()
    return summary


def _import_purchase_order_lines(
    db: Session, ws: Any, filename: str = "workbook.xlsx", start_t: Optional[float] = None
) -> SheetImportSummary:
    summary = SheetImportSummary(sheet_name="Purchase_Order_Lines")
    rows, header_mappings = _get_sheet_rows_and_mappings(ws, "Purchase_Order_Lines")
    summary.header_mappings = header_mappings

    for idx, row in enumerate(rows, start=2):
        po_num = _normalize(row.get("po_number"))
        p_code = _normalize(row.get("plant_code"))
        m_code = _normalize(row.get("material_code"))
        l_num = _parse_int(row.get("line_number"), 10)
        ord_qty = _parse_float(row.get("ordered_qty"), 0.0)
        rec_qty = _parse_float(row.get("received_qty"), 0.0)

        if not po_num:
            _raise_missing_field_error("Purchase_Order_Lines", "po_number", filename, start_t)
        if not m_code:
            _raise_missing_field_error("Purchase_Order_Lines", "material_code", filename, start_t)

        if ord_qty < rec_qty:
            _raise_import_error(
                filename=filename,
                sheet_name="Purchase_Order_Lines",
                row_number=idx,
                column_name="ordered_qty",
                received_value=ord_qty,
                expected_value=f">= received_qty ({rec_qty})",
                validation_rule="Order Quantity >= Received Quantity",
                reason=f"Ordered quantity ({ord_qty}) must be >= Received quantity ({rec_qty}).",
                phase="Business Rule Validation",
                start_time=start_t,
            )

        po = db.query(PurchaseOrder).filter(PurchaseOrder.po_number == po_num).first()
        material = db.query(Material).filter(Material.code == m_code).first()
        plant = db.query(Plant).filter(Plant.code == p_code).first() if p_code else None

        if p_code and not plant:
            _raise_import_error(
                filename=filename,
                sheet_name="Purchase_Order_Lines",
                row_number=idx,
                column_name="plant_code",
                received_value=p_code,
                expected_value="Existing Plant Master Code",
                validation_rule="Foreign Key Constraint",
                reason=f"Plant '{p_code}' does not exist in Plant_Master.",
                phase="Foreign Key Validation",
                start_time=start_t,
            )

        if not po:
            _raise_import_error(
                filename=filename,
                sheet_name="Purchase_Order_Lines",
                row_number=idx,
                column_name="po_number",
                received_value=po_num,
                expected_value="Existing Purchase Order Number",
                validation_rule="Foreign Key Constraint",
                reason=f"PO '{po_num}' does not exist in Purchase_Orders.",
                phase="Foreign Key Validation",
                start_time=start_t,
            )
        if not material:
            _raise_import_error(
                filename=filename,
                sheet_name="Purchase_Order_Lines",
                row_number=idx,
                column_name="material_code",
                received_value=m_code,
                expected_value="Existing Material Master Code",
                validation_rule="Foreign Key Constraint",
                reason=f"Material '{m_code}' does not exist in Material_Master.",
                phase="Foreign Key Validation",
                start_time=start_t,
            )

        exp_deliv = _parse_date_val(row.get("expected_delivery_date")) or (po.expected_delivery_date if po else None) or date.today()

        pol = PurchaseOrderLine(
            po_id=po.id,
            plant_id=plant.id if plant else None,
            line_number=l_num,
            material_id=material.id,
            order_quantity=ord_qty,
            quantity=ord_qty,
            open_quantity=max(0.0, ord_qty - rec_qty),
            uom=material.base_uom or "KG",
            expected_delivery_date=exp_deliv,
        )
        db.add(pol)

        if plant and not po.plant_id:
            po.plant_id = plant.id

        summary.imported += 1

    db.flush()
    return summary


def _import_monthly_production_plan(
    db: Session, ws: Any, filename: str = "workbook.xlsx", start_t: Optional[float] = None
) -> SheetImportSummary:
    summary = SheetImportSummary(sheet_name="Monthly_Production_Plan")
    rows, header_mappings = _get_sheet_rows_and_mappings(ws, "Monthly_Production_Plan")
    summary.header_mappings = header_mappings

    seen_plans: dict[tuple[int, int, int, int], MonthlyProductionPlan] = {}

    for idx, row in enumerate(rows, start=2):
        p_code = _normalize(row.get("plant_code"))
        m_code = _normalize(row.get("material_code"))
        yr, mn = _parse_period(row)
        qty = _parse_float(row.get("planned_production_qty"), 0.0)

        raw_period_val = row.get("period") or row.get("month") or row.get("year")
        logger.info(f"[PERIOD_TRACE] Row {idx}: Raw Period={raw_period_val!r} -> Parsed Year={yr}, Parsed Month={mn}")

        if not p_code:
            _raise_missing_field_error("Monthly_Production_Plan", "plant_code", filename, start_t)
        if not m_code:
            _raise_missing_field_error("Monthly_Production_Plan", "material_code", filename, start_t)

        if qty <= 0:
            _raise_import_error(
                filename=filename,
                sheet_name="Monthly_Production_Plan",
                row_number=idx,
                column_name="planned_production_qty",
                received_value=qty,
                expected_value="Number > 0",
                validation_rule="Planned Production Quantity > 0",
                reason=f"Planned production quantity must be > 0 (got {qty}).",
                phase="Business Rule Validation",
                start_time=start_t,
            )

        plant = db.query(Plant).filter(Plant.code == p_code).first()
        material = db.query(Material).filter(Material.code == m_code).first()

        if not plant:
            _raise_import_error(
                filename=filename,
                sheet_name="Monthly_Production_Plan",
                row_number=idx,
                column_name="plant_code",
                received_value=p_code,
                expected_value="Existing Plant Master Code",
                validation_rule="Foreign Key Constraint",
                reason=f"Plant '{p_code}' does not exist in Plant_Master.",
                phase="Foreign Key Validation",
                start_time=start_t,
            )
        if not material:
            _raise_import_error(
                filename=filename,
                sheet_name="Monthly_Production_Plan",
                row_number=idx,
                column_name="material_code",
                received_value=m_code,
                expected_value="Existing Material Master Code",
                validation_rule="Foreign Key Constraint",
                reason=f"Material '{m_code}' does not exist in Material_Master.",
                phase="Foreign Key Validation",
                start_time=start_t,
            )

        key = (plant.id, material.id, yr, mn)

        if key in seen_plans:
            _raise_import_error(
                filename=filename,
                sheet_name="Monthly_Production_Plan",
                row_number=idx,
                column_name="Year/Month",
                received_value=f"Year {yr}, Month {mn}",
                expected_value="Unique (Plant, Material, Year, Month) per row",
                validation_rule="Duplicate Key Constraint",
                reason=f"Duplicate Monthly Production Plan entry for Plant '{p_code}', Material '{m_code}', Year {yr}, Month {mn} at row {idx}.",
                phase="Business Rule Validation",
                start_time=start_t,
            )

        existing = db.query(MonthlyProductionPlan).filter(
            MonthlyProductionPlan.plant_id == plant.id,
            MonthlyProductionPlan.material_id == material.id,
            MonthlyProductionPlan.year == yr,
            MonthlyProductionPlan.month == mn,
        ).first()

        if existing:
            existing.planned_production_qty = qty
            seen_plans[key] = existing
            summary.updated += 1
        else:
            plan = MonthlyProductionPlan(
                plant_id=plant.id,
                material_id=material.id,
                year=yr,
                month=mn,
                planned_production_qty=qty,
            )
            db.add(plan)
            seen_plans[key] = plan
            summary.imported += 1

    db.flush()
    return summary


def _import_daily_ibp_plan(
    db: Session, ws: Any, filename: str = "workbook.xlsx", start_t: Optional[float] = None
) -> SheetImportSummary:
    summary = SheetImportSummary(sheet_name="Daily_IBP_Plan")
    rows, header_mappings = _get_sheet_rows_and_mappings(ws, "Daily_IBP_Plan")
    summary.header_mappings = header_mappings

    for hm in header_mappings:
        logger.info(f"[IBP_TRACE] Raw Header -> Canonical Field: {hm.raw_header!r} -> {hm.mapped_field!r}")

    for idx, row in enumerate(rows, start=2):
        p_code = _normalize(row.get("plant_code"))
        m_code = _normalize(row.get("material_code"))
        p_date = _parse_date_val(row.get("plan_date")) or date.today()
        qty = _parse_float(row.get("required_daily_qty"), 0.0)

        logger.info(f"[IBP_TRACE] Row {idx} Dictionary: {row}")
        logger.info(f"[IBP_TRACE] Row {idx} qty = {qty}")

        if not p_code:
            _raise_missing_field_error("Daily_IBP_Plan", "plant_code", filename, start_t)
        if not m_code:
            _raise_missing_field_error("Daily_IBP_Plan", "material_code", filename, start_t)

        if qty <= 0:
            _raise_import_error(
                filename=filename,
                sheet_name="Daily_IBP_Plan",
                row_number=idx,
                column_name="required_daily_qty",
                received_value=qty,
                expected_value="Number > 0",
                validation_rule="Required Daily Quantity > 0",
                reason=f"Required daily quantity must be > 0 (got {qty}).",
                phase="Business Rule Validation",
                start_time=start_t,
            )

        plant = db.query(Plant).filter(Plant.code == p_code).first()
        material = db.query(Material).filter(Material.code == m_code).first()

        if not plant:
            _raise_import_error(
                filename=filename,
                sheet_name="Daily_IBP_Plan",
                row_number=idx,
                column_name="plant_code",
                received_value=p_code,
                expected_value="Existing Plant Master Code",
                validation_rule="Foreign Key Constraint",
                reason=f"Plant '{p_code}' does not exist in Plant_Master.",
                phase="Foreign Key Validation",
                start_time=start_t,
            )
        if not material:
            _raise_import_error(
                filename=filename,
                sheet_name="Daily_IBP_Plan",
                row_number=idx,
                column_name="material_code",
                received_value=m_code,
                expected_value="Existing Material Master Code",
                validation_rule="Foreign Key Constraint",
                reason=f"Material '{m_code}' does not exist in Material_Master.",
                phase="Foreign Key Validation",
                start_time=start_t,
            )

        existing = db.query(DailyIBPPlan).filter(
            DailyIBPPlan.plant_id == plant.id,
            DailyIBPPlan.material_id == material.id,
            DailyIBPPlan.plan_date == p_date,
        ).first()

        if existing:
            existing.required_daily_qty = qty
            summary.updated += 1
        else:
            ibp = DailyIBPPlan(
                plant_id=plant.id,
                material_id=material.id,
                plan_date=p_date,
                required_daily_qty=qty,
            )
            db.add(ibp)
            summary.imported += 1

    db.flush()
    return summary


# --------------------------------------------------------------------------
# WORKBOOK 3 PARSERS
# --------------------------------------------------------------------------

def _import_rm_totality_mapping(
    db: Session, ws: Any, filename: str = "workbook.xlsx", start_t: Optional[float] = None
) -> SheetImportSummary:
    summary = SheetImportSummary(sheet_name="RM_Totality_Mapping")
    rows, header_mappings = _get_sheet_rows_and_mappings(ws, "RM_Totality_Mapping")
    summary.header_mappings = header_mappings

    for idx, row in enumerate(rows, start=2):
        p_code = _normalize(row.get("plant_code"))
        rm_code = _normalize(row.get("rm_material_code"))
        fg_grp = _normalize(row.get("totality_group_code") or row.get("fg_material_code") or "DEFAULT_GROUP")
        ratio = _parse_float(row.get("contribution_ratio"), 1.0)

        if not p_code:
            _raise_missing_field_error("RM_Totality_Mapping", "plant_code", filename, start_t)
        if not rm_code:
            _raise_missing_field_error("RM_Totality_Mapping", "rm_material_code", filename, start_t)

        if ratio <= 0:
            _raise_import_error(
                filename=filename,
                sheet_name="RM_Totality_Mapping",
                row_number=idx,
                column_name="contribution_ratio",
                received_value=ratio,
                expected_value="Number > 0",
                validation_rule="Contribution Ratio > 0",
                reason=f"Contribution ratio must be > 0 (got {ratio}).",
                phase="Business Rule Validation",
                start_time=start_t,
            )

        plant = db.query(Plant).filter(Plant.code == p_code).first()
        rm_mat = db.query(Material).filter(Material.code == rm_code).first()

        if not plant:
            _raise_import_error(
                filename=filename,
                sheet_name="RM_Totality_Mapping",
                row_number=idx,
                column_name="plant_code",
                received_value=p_code,
                expected_value="Existing Plant Master Code",
                validation_rule="Foreign Key Constraint",
                reason=f"Plant '{p_code}' does not exist in Plant_Master.",
                phase="Foreign Key Validation",
                start_time=start_t,
            )
        if not rm_mat:
            _raise_import_error(
                filename=filename,
                sheet_name="RM_Totality_Mapping",
                row_number=idx,
                column_name="rm_material_code",
                received_value=rm_code,
                expected_value="Existing Material Master Code",
                validation_rule="Foreign Key Constraint",
                reason=f"RM Material '{rm_code}' does not exist in Material_Master.",
                phase="Foreign Key Validation",
                start_time=start_t,
            )

        existing = db.query(RMTotalityMapping).filter(
            RMTotalityMapping.plant_id == plant.id,
            RMTotalityMapping.rm_material_id == rm_mat.id,
            RMTotalityMapping.fg_group_name == fg_grp,
        ).first()

        if existing:
            existing.consumption_ratio = ratio
            summary.updated += 1
        else:
            tot = RMTotalityMapping(
                plant_id=plant.id,
                rm_material_id=rm_mat.id,
                fg_group_name=fg_grp,
                consumption_ratio=ratio,
            )
            db.add(tot)
            summary.imported += 1

    db.flush()
    return summary


def _import_pm_mapping(
    db: Session, ws: Any, filename: str = "workbook.xlsx", start_t: Optional[float] = None
) -> SheetImportSummary:
    summary = SheetImportSummary(sheet_name="PM_Mapping")
    rows, header_mappings = _get_sheet_rows_and_mappings(ws, "PM_Mapping")
    summary.header_mappings = header_mappings

    for idx, row in enumerate(rows, start=2):
        fg_code = _normalize(row.get("fg_material_code"))
        pm_code = _normalize(row.get("pm_material_code"))
        qty = _parse_float(row.get("usage_qty_per_fg"), 1.0)

        if not fg_code:
            _raise_missing_field_error("PM_Mapping", "fg_material_code", filename, start_t)
        if not pm_code:
            _raise_missing_field_error("PM_Mapping", "pm_material_code", filename, start_t)

        if qty <= 0:
            _raise_import_error(
                filename=filename,
                sheet_name="PM_Mapping",
                row_number=idx,
                column_name="usage_qty_per_fg",
                received_value=qty,
                expected_value="Number > 0",
                validation_rule="Usage Quantity > 0",
                reason=f"Usage quantity must be > 0 (got {qty}).",
                phase="Business Rule Validation",
                start_time=start_t,
            )

        fg_mat = db.query(Material).filter(Material.code == fg_code).first()
        pm_mat = db.query(Material).filter(Material.code == pm_code).first()

        if not fg_mat:
            _raise_import_error(
                filename=filename,
                sheet_name="PM_Mapping",
                row_number=idx,
                column_name="fg_material_code",
                received_value=fg_code,
                expected_value="Existing Material Master Code",
                validation_rule="Foreign Key Constraint",
                reason=f"FG Material '{fg_code}' does not exist in Material_Master.",
                phase="Foreign Key Validation",
                start_time=start_t,
            )
        if not pm_mat:
            _raise_import_error(
                filename=filename,
                sheet_name="PM_Mapping",
                row_number=idx,
                column_name="pm_material_code",
                received_value=pm_code,
                expected_value="Existing Material Master Code",
                validation_rule="Foreign Key Constraint",
                reason=f"PM Material '{pm_code}' does not exist in Material_Master.",
                phase="Foreign Key Validation",
                start_time=start_t,
            )

        existing = db.query(BOM).filter(
            BOM.fg_material_id == fg_mat.id,
            BOM.component_material_id == pm_mat.id,
        ).first()

        if existing:
            existing.required_quantity = qty
            summary.updated += 1
        else:
            bom = BOM(
                fg_material_id=fg_mat.id,
                component_material_id=pm_mat.id,
                required_quantity=qty,
                unit_of_measure=pm_mat.base_uom or "KG",
            )
            db.add(bom)
            summary.imported += 1

    db.flush()
    return summary


def _import_pm_overrides(
    db: Session, ws: Any, filename: str = "workbook.xlsx", start_t: Optional[float] = None
) -> SheetImportSummary:
    summary = SheetImportSummary(sheet_name="PM_Overrides")
    rows, header_mappings = _get_sheet_rows_and_mappings(ws, "PM_Overrides")
    summary.header_mappings = header_mappings

    for idx, row in enumerate(rows, start=2):
        p_code = _normalize(row.get("plant_code"))
        fg_code = _normalize(row.get("fg_material_code"))
        pm_code = _normalize(row.get("pm_material_code"))
        ov_ratio = _parse_float(row.get("override_usage_qty"), 1.0)
        notes = _normalize(row.get("reason")) or None

        if not p_code:
            _raise_missing_field_error("PM_Overrides", "plant_code", filename, start_t)
        if not fg_code:
            _raise_missing_field_error("PM_Overrides", "fg_material_code", filename, start_t)
        if not pm_code:
            _raise_missing_field_error("PM_Overrides", "pm_material_code", filename, start_t)

        if ov_ratio <= 0:
            _raise_import_error(
                filename=filename,
                sheet_name="PM_Overrides",
                row_number=idx,
                column_name="override_usage_qty",
                received_value=ov_ratio,
                expected_value="Number > 0",
                validation_rule="Override Usage Quantity > 0",
                reason=f"Override usage quantity must be > 0 (got {ov_ratio}).",
                phase="Business Rule Validation",
                start_time=start_t,
            )

        plant = db.query(Plant).filter(Plant.code == p_code).first()
        fg_mat = db.query(Material).filter(Material.code == fg_code).first()
        pm_mat = db.query(Material).filter(Material.code == pm_code).first()

        if not plant:
            _raise_import_error(
                filename=filename,
                sheet_name="PM_Overrides",
                row_number=idx,
                column_name="plant_code",
                received_value=p_code,
                expected_value="Existing Plant Master Code",
                validation_rule="Foreign Key Constraint",
                reason=f"Plant '{p_code}' does not exist in Plant_Master.",
                phase="Foreign Key Validation",
                start_time=start_t,
            )
        if not fg_mat:
            _raise_import_error(
                filename=filename,
                sheet_name="PM_Overrides",
                row_number=idx,
                column_name="fg_material_code",
                received_value=fg_code,
                expected_value="Existing Material Master Code",
                validation_rule="Foreign Key Constraint",
                reason=f"FG Material '{fg_code}' does not exist in Material_Master.",
                phase="Foreign Key Validation",
                start_time=start_t,
            )
        if not pm_mat:
            _raise_import_error(
                filename=filename,
                sheet_name="PM_Overrides",
                row_number=idx,
                column_name="pm_material_code",
                received_value=pm_code,
                expected_value="Existing Material Master Code",
                validation_rule="Foreign Key Constraint",
                reason=f"PM Material '{pm_code}' does not exist in Material_Master.",
                phase="Foreign Key Validation",
                start_time=start_t,
            )

        existing = db.query(PMOverride).filter(
            PMOverride.plant_id == plant.id,
            PMOverride.fg_material_id == fg_mat.id,
            PMOverride.pm_material_id == pm_mat.id,
        ).first()

        if existing:
            existing.override_ratio = ov_ratio
            existing.notes = notes
            summary.updated += 1
        else:
            ov = PMOverride(
                plant_id=plant.id,
                fg_material_id=fg_mat.id,
                pm_material_id=pm_mat.id,
                override_ratio=ov_ratio,
                notes=notes,
            )
            db.add(ov)
            summary.imported += 1

    db.flush()
    return summary

