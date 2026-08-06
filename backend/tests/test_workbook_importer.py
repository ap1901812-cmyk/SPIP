import io
import openpyxl
import pytest
from sqlalchemy.orm import Session

from app.db.models.domain import (
    BOM,
    ConsumptionHistory,
    DailyIBPPlan,
    InventorySnapshot,
    Material,
    MonthlyProductionPlan,
    PMOverride,
    Plant,
    PlantMaterial,
    PurchaseOrder,
    PurchaseOrderLine,
    RMTotalityMapping,
    VehicleMaster,
    Vendor,
    VendorMaterial,
)
from app.services.planning.orchestrator import execute_full_planning_pipeline
from app.services.workbook_importer import (
    WorkbookImportError,
    _map_header_to_field,
    _parse_period,
    import_enterprise_workbook,
)


def _create_wb1_bytes() -> bytes:
    wb = openpyxl.Workbook()

    # Plant_Master
    ws1 = wb.active
    ws1.title = "Plant_Master"
    ws1.append(["plant_code", "plant_name", "location", "storage_capacity_tons", "is_active"])
    ws1.append(["PLANT-UAT1", "Mumbai Master Plant", "Mumbai", 15000, "True"])

    # Material_Master
    ws2 = wb.create_sheet("Material_Master")
    ws2.append(["material_code", "material_name", "material_type", "uom", "lead_time_1_days", "lead_time_2_days", "safety_stock_1_qty", "safety_stock_2_qty", "abc_classification"])
    ws2.append(["RM-UAT1", "Raw Chemical A", "RM", "KG", 14, 7, 100, 50, "A"])
    ws2.append(["PM-UAT1", "Packaging Drum 200L", "PM", "EA", 10, 5, 200, 100, "B"])
    ws2.append(["FG-UAT1", "Finished Chemical Solution", "FG", "KG", 0, 0, 0, 0, "A"])

    # Vendor_Master
    ws3 = wb.create_sheet("Vendor_Master")
    ws3.append(["vendor_code", "vendor_name", "contact_email", "capacity_tons_per_month", "is_active"])
    ws3.append(["VEND-UAT1", "Global Supplier Ltd", "supplier@global.com", 1000, "True"])

    # Vendor_Material_Mapping
    ws4 = wb.create_sheet("Vendor_Material_Mapping")
    ws4.append(["vendor_code", "material_code", "is_primary", "min_order_qty"])
    ws4.append(["VEND-UAT1", "RM-UAT1", "True", 500])

    # Vehicle_Master
    ws5 = wb.create_sheet("Vehicle_Master")
    ws5.append(["vehicle_type_code", "vehicle_type_name", "capacity_tons", "capacity_cbm", "cost_per_km"])
    ws5.append(["TRUCK-25T", "25 Ton Heavy Carrier", 25.0, 60.0, 20.0])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _create_wb2_bytes() -> bytes:
    wb = openpyxl.Workbook()

    # Inventory_Snapshot
    ws1 = wb.active
    ws1.title = "Inventory_Snapshot"
    ws1.append(["plant_code", "material_code", "current_stock_qty", "reserved_stock_qty", "snapshot_date"])
    ws1.append(["PLANT-UAT1", "RM-UAT1", 5000.0, 500.0, "2026-08-01"])
    ws1.append(["PLANT-UAT1", "PM-UAT1", 2000.0, 0.0, "2026-08-01"])

    # Consumption_History
    ws2 = wb.create_sheet("Consumption_History")
    ws2.append(["plant_code", "material_code", "posting_date", "quantity_consumed"])
    ws2.append(["PLANT-UAT1", "RM-UAT1", "2026-07-28", 200.0])
    ws2.append(["PLANT-UAT1", "RM-UAT1", "2026-07-29", 250.0])

    # Purchase_Orders (Header without plant_code requirement)
    ws3 = wb.create_sheet("Purchase_Orders")
    ws3.append(["po_number", "vendor_code", "po_date", "expected_delivery_date", "status"])
    ws3.append(["PO-UAT-9001", "VEND-UAT1", "2026-08-01", "2026-08-15", "OPEN"])

    # Purchase_Order_Lines (With plant_code)
    ws4 = wb.create_sheet("Purchase_Order_Lines")
    ws4.append(["po_number", "plant_code", "material_code", "line_number", "ordered_qty", "received_qty"])
    ws4.append(["PO-UAT-9001", "PLANT-UAT1", "RM-UAT1", 10, 1000.0, 0.0])

    # Monthly_Production_Plan
    ws5 = wb.create_sheet("Monthly_Production_Plan")
    ws5.append(["plant_code", "material_code", "year", "month", "planned_production_qty"])
    ws5.append(["PLANT-UAT1", "FG-UAT1", 2026, 8, 10000.0])

    # Daily_IBP_Plan
    ws6 = wb.create_sheet("Daily_IBP_Plan")
    ws6.append(["plant_code", "material_code", "plan_date", "required_daily_qty"])
    ws6.append(["PLANT-UAT1", "FG-UAT1", "2026-08-05", 300.0])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _create_wb3_bytes() -> bytes:
    wb = openpyxl.Workbook()

    # RM_Totality_Mapping
    ws1 = wb.active
    ws1.title = "RM_Totality_Mapping"
    ws1.append(["plant_code", "rm_material_code", "totality_group_code", "contribution_ratio"])
    ws1.append(["PLANT-UAT1", "RM-UAT1", "CHEMICAL_GROUP_A", 1.0])

    # PM_Mapping
    ws2 = wb.create_sheet("PM_Mapping")
    ws2.append(["plant_code", "fg_material_code", "pm_material_code", "usage_qty_per_fg"])
    ws2.append(["PLANT-UAT1", "FG-UAT1", "PM-UAT1", 1.0])

    # PM_Overrides
    ws3 = wb.create_sheet("PM_Overrides")
    ws3.append(["plant_code", "fg_material_code", "pm_material_code", "override_usage_qty", "reason"])
    ws3.append(["PLANT-UAT1", "FG-UAT1", "PM-UAT1", 1.2, "Summer adjustment"])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_enterprise_workbook_import_pipeline(db_session: Session) -> None:
    # 1. Import Workbook 1 (Master Data)
    wb1_bytes = _create_wb1_bytes()
    res1 = import_enterprise_workbook(db_session, wb1_bytes, "Workbook_1_Master_Data.xlsx", replace_existing=True)
    assert res1.success is True
    assert res1.workbook_type == "Workbook 1: Master Data"
    assert res1.total_imported >= 5

    plant = db_session.query(Plant).filter(Plant.code == "PLANT-UAT1").first()
    assert plant is not None
    assert plant.storage_capacity_tons == 15000

    rm = db_session.query(Material).filter(Material.code == "RM-UAT1").first()
    assert rm is not None
    assert rm.material_type == "RM"

    # 2. Import Workbook 2 (Planning Data)
    wb2_bytes = _create_wb2_bytes()
    res2 = import_enterprise_workbook(db_session, wb2_bytes, "Workbook_2_Planning_Data.xlsx")
    assert res2.success is True
    assert res2.workbook_type == "Workbook 2: Planning Data"
    assert res2.total_imported >= 6

    snap = db_session.query(InventorySnapshot).filter(InventorySnapshot.material_id == rm.id).first()
    assert snap is not None
    assert snap.usable_physical_stock == 5000.0

    po = db_session.query(PurchaseOrder).filter(PurchaseOrder.po_number == "PO-UAT-9001").first()
    assert po is not None
    po_line = db_session.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == po.id).first()
    assert po_line is not None
    assert po_line.plant_id == plant.id

    # 3. Import Workbook 3 (SPIP Configuration)
    wb3_bytes = _create_wb3_bytes()
    res3 = import_enterprise_workbook(db_session, wb3_bytes, "Workbook_3_SPIP_Configuration.xlsx")
    assert res3.success is True
    assert res3.workbook_type == "Workbook 3: SPIP Configuration"
    assert res3.total_imported >= 3

    tot = db_session.query(RMTotalityMapping).filter(RMTotalityMapping.rm_material_id == rm.id).first()
    assert tot is not None
    assert tot.fg_group_name == "CHEMICAL_GROUP_A"

    ov = db_session.query(PMOverride).filter(PMOverride.plant_id == plant.id).first()
    assert ov is not None
    assert ov.override_ratio == 1.2

    # 4. Run Planning Pipeline against ingested UAT Workbooks
    planning_res = execute_full_planning_pipeline(db_session, plant_code="PLANT-UAT1", material_code="RM-UAT1")
    print("PLANNING FAILURE REASON:", planning_res.execution_metadata.failure_reason)
    assert planning_res.plant_code == "PLANT-UAT1"
    assert planning_res.execution_metadata.status == "SUCCESS"


def test_intelligent_header_mapping_aliases(db_session: Session) -> None:
    """Test enterprise header aliases (Plant_ID, Plant_Name, FG_Material_ID, RM_Material_ID, Consumption_Factor)."""
    # Build Workbook 1 with Enterprise Aliases: Plant_ID, Plant_Name, Storage_Capacity
    wb1 = openpyxl.Workbook()
    ws1 = wb1.active
    ws1.title = "Plant_Master"
    ws1.append(["Plant_ID", "Plant_Name", "Location", "Storage_Capacity", "is_active"])
    ws1.append(["PLANT-ALIAS1", "Delhi Enterprise Plant", "Delhi", 20000, "True"])

    ws2 = wb1.create_sheet("Material_Master")
    ws2.append(["Material ID", "Item Name", "Material Type", "Base UOM", "Procurement Lead Time", "Lead Time 2", "Safety Stock", "Safety Stock 2", "ABC Class"])
    ws2.append(["RM-ALIAS1", "Raw Material Resin", "RM", "KG", 15, 8, 150, 75, "A"])
    ws2.append(["PM-ALIAS1", "Packaging Carton Box", "PM", "EA", 7, 3, 300, 150, "B"])
    ws2.append(["FG-ALIAS1", "Finished Molded Part", "FG", "KG", 1, 1, 1, 1, "A"])

    ws3 = wb1.create_sheet("Vendor_Master")
    ws3.append(["Supplier Code", "Supplier Name", "Contact Email", "Vendor Capacity", "is_active"])
    ws3.append(["VEND-ALIAS1", "Alpha Resins Corp", "sales@alpha.com", 2000, "True"])

    ws4 = wb1.create_sheet("Vendor_Material_Mapping")
    ws4.append(["Supplier Code", "Item Code", "is_primary", "min_order_qty"])
    ws4.append(["VEND-ALIAS1", "RM-ALIAS1", "True", 100])

    ws5 = wb1.create_sheet("Vehicle_Master")
    ws5.append(["Vehicle Code", "Vehicle Name", "Truck Capacity", "Capacity CBM", "Cost Per KM"])
    ws5.append(["TRUCK-30T", "30 Ton Mega Carrier", 30.0, 70.0, 25.0])

    buf1 = io.BytesIO()
    wb1.save(buf1)

    res1 = import_enterprise_workbook(db_session, buf1.getvalue(), "Enterprise_WB1.xlsx", replace_existing=True)
    assert res1.success is True
    assert res1.workbook_type == "Workbook 1: Master Data"

    p = db_session.query(Plant).filter(Plant.code == "PLANT-ALIAS1").first()
    assert p is not None
    assert p.name == "Delhi Enterprise Plant"
    assert p.storage_capacity_tons == 20000

    # Build Workbook 3 with Enterprise Aliases: FG_Material_ID, RM_Material_ID, Consumption_Factor
    wb3 = openpyxl.Workbook()
    ws3_1 = wb3.active
    ws3_1.title = "RM_Totality_Mapping"
    ws3_1.append(["Plant ID", "RM_Material_ID", "Totality Group", "Consumption_Factor"])
    ws3_1.append(["PLANT-ALIAS1", "RM-ALIAS1", "RESIN_GROUP", 1.5])

    ws3_2 = wb3.create_sheet("PM_Mapping")
    ws3_2.append(["FG_Material_ID", "PM_Material_ID", "Consumption_Factor"])
    ws3_2.append(["FG-ALIAS1", "PM-ALIAS1", 2.0])

    ws3_3 = wb3.create_sheet("PM_Overrides")
    ws3_3.append(["Plant ID", "FG_Material_ID", "PM_Material_ID", "Override Usage Qty", "Reason"])
    ws3_3.append(["PLANT-ALIAS1", "FG-ALIAS1", "PM-ALIAS1", 2.5, "High heat adjustment"])

    buf3 = io.BytesIO()
    wb3.save(buf3)

    res3 = import_enterprise_workbook(db_session, buf3.getvalue(), "Enterprise_WB3.xlsx")
    assert res3.success is True
    assert res3.workbook_type == "Workbook 3: SPIP Configuration"

    tot = db_session.query(RMTotalityMapping).filter(RMTotalityMapping.plant_id == p.id).first()
    assert tot is not None
    assert tot.consumption_ratio == 1.5


def test_transactional_rollback_on_fk_error(db_session: Session) -> None:
    # Build invalid Workbook 2 referencing non-existent plant
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inventory_Snapshot"
    ws.append(["plant_code", "material_code", "current_stock_qty"])
    ws.append(["NON_EXISTENT_PLANT", "NON_EXISTENT_MAT", 999.0])

    ws2 = wb.create_sheet("Consumption_History")
    ws2.append(["plant_code", "material_code", "quantity_consumed"])

    ws3 = wb.create_sheet("Purchase_Orders")
    ws3.append(["po_number", "vendor_code", "plant_code"])

    ws4 = wb.create_sheet("Purchase_Order_Lines")
    ws4.append(["po_number", "material_code", "ordered_qty"])

    ws5 = wb.create_sheet("Monthly_Production_Plan")
    ws5.append(["plant_code", "material_code", "planned_production_qty"])

    ws6 = wb.create_sheet("Daily_IBP_Plan")
    ws6.append(["plant_code", "material_code", "required_daily_qty"])

    buf = io.BytesIO()
    wb.save(buf)

    # Initial inventory snapshots count
    initial_count = db_session.query(InventorySnapshot).count()

    with pytest.raises(WorkbookImportError) as exc_info:
        import_enterprise_workbook(db_session, buf.getvalue(), "Invalid.xlsx")

    # Verify structured error details
    err = exc_info.value
    assert err.details is not None
    assert err.details["workbook_name"] == "Invalid.xlsx"
    assert err.details["sheet_name"] == "Inventory_Snapshot"
    assert err.details["row_number"] == 2
    assert err.details["column_name"] == "plant_code"
    assert err.details["received_value"] == "NON_EXISTENT_PLANT"
    assert err.details["validation_rule"] == "Foreign Key Constraint"

    # Verify rollback: 0 records inserted
    assert db_session.query(InventorySnapshot).count() == initial_count


def test_sheet_aware_header_mapping_quantity_resolution() -> None:
    """Requirement 6: Prove five different worksheets containing the same header 'Quantity'
    map to five different internal fields correctly.
    """
    # 1. Purchase_Order_Lines: 'Quantity' -> 'ordered_qty'
    assert _map_header_to_field("Quantity", "Purchase_Order_Lines") == "ordered_qty"
    assert _map_header_to_field("quantity", "Purchase_Order_Lines") == "ordered_qty"
    assert _map_header_to_field("orderQuantity", "Purchase_Order_Lines") == "ordered_qty"

    # 2. Consumption_History: 'Quantity' -> 'quantity_consumed'
    assert _map_header_to_field("Quantity", "Consumption_History") == "quantity_consumed"
    assert _map_header_to_field("quantity", "Consumption_History") == "quantity_consumed"
    assert _map_header_to_field("consumed_qty", "Consumption_History") == "quantity_consumed"

    # 3. Inventory_Snapshot: 'Quantity' -> 'current_stock_qty'
    assert _map_header_to_field("Quantity", "Inventory_Snapshot") == "current_stock_qty"
    assert _map_header_to_field("quantity", "Inventory_Snapshot") == "current_stock_qty"
    assert _map_header_to_field("usable_stock", "Inventory_Snapshot") == "current_stock_qty"

    # 4. Monthly_Production_Plan: 'Quantity' -> 'planned_production_qty'
    assert _map_header_to_field("Quantity", "Monthly_Production_Plan") == "planned_production_qty"
    assert _map_header_to_field("quantity", "Monthly_Production_Plan") == "planned_production_qty"
    assert _map_header_to_field("planned_qty", "Monthly_Production_Plan") == "planned_production_qty"

    # 5. Daily_IBP_Plan: 'Quantity' -> 'required_daily_qty'
    assert _map_header_to_field("Quantity", "Daily_IBP_Plan") == "required_daily_qty"
    assert _map_header_to_field("quantity", "Daily_IBP_Plan") == "required_daily_qty"
    assert _map_header_to_field("ibp_req_qty", "Daily_IBP_Plan") == "required_daily_qty"


def test_parse_period_formats() -> None:
    """Test period parsing for 2026-08, 2026-09, 2026/10, Excel datetime, and separate Year + Month columns."""
    from datetime import datetime

    # 1. '2026-08' -> (2026, 8)
    assert _parse_period({"month": "2026-08"}) == (2026, 8)
    assert _parse_period({"period": "2026-08"}) == (2026, 8)

    # 2. '2026-09' -> (2026, 9)
    assert _parse_period({"month": "2026-09"}) == (2026, 9)

    # 3. '2026/10' -> (2026, 10)
    assert _parse_period({"month": "2026/10"}) == (2026, 10)

    # 4. Excel datetime object -> (2026, 11)
    dt_val = datetime(2026, 11, 15, 0, 0, 0)
    assert _parse_period({"month": dt_val}) == (2026, 11)

    # 5. Separate Year + Month columns -> (2026, 8)
    assert _parse_period({"year": 2026, "month": 8}) == (2026, 8)
    assert _parse_period({"year": "2026", "month": "8"}) == (2026, 8)


def test_daily_ibp_plan_header_variations() -> None:
    """Requirement 4: Verify every supported header variation maps to canonical field 'required_daily_qty'."""
    variations = [
        "Required_Daily_Qty",
        "Required_Daily_Quantity",
        "Daily_Qty",
        "Daily_Quantity",
        "Required_Quantity",
        "Daily_IBP_Qty",
        "Daily_IBP_Quantity",
        "Planned_Daily_Qty",
        "Forecast_Qty",
        "Forecast_Quantity",
        "Quantity",
        "Qty",
    ]
    for header in variations:
        assert _map_header_to_field(header, "Daily_IBP_Plan") == "required_daily_qty", f"Header {header} failed to map to required_daily_qty"




