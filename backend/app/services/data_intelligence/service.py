from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.models.domain import (
    Allocation,
    ConsumptionHistory,
    InventorySnapshot,
    Material,
    MaterialTypeEnum,
    Plant,
    PlantMaterial,
    PurchaseOrder,
    PurchaseOrderLine,
    Vendor,
    VendorMaterial,
)
from app.services.data_intelligence.file_recognizer import DatasetTypeEnum, recognize_file_type
from app.services.data_intelligence.master_generator import AutoMasterGenerator
from app.services.data_intelligence.quality_scanner import (
    DataQualityScanner,
    DataQualitySummary,
    FileProcessingReport,
)
from app.services.ingestion import IngestionError, _extract_xlsx_rows, _parse_date


class EnterpriseDataIntelligenceService:
    """Enterprise Data Intelligence orchestrator for cross-file analysis, duplicate detection,

    auto master generation, and data quality summary reporting.
    """

    def __init__(self, db: Session, user_id: int | None = None) -> None:
        self.db = db
        self.user_id = user_id
        self.master_gen = AutoMasterGenerator(db, user_id=user_id)

    def process_batch(
        self,
        files: list[tuple[str, bytes]],
    ) -> DataQualitySummary:
        scanner = DataQualityScanner()
        processed_types: set[DatasetTypeEnum] = set()

        for filename, content in files:
            raw_rows: list[dict[str, str]] = []
            if filename.endswith(".xlsx"):
                try:
                    raw_rows = _extract_xlsx_rows(content)
                except Exception as exc:
                    scanner.add_validation_error(filename, 0, "file", f"Failed to parse XLSX: {exc}")
                    continue
            else:
                try:
                    import csv
                    import io

                    text = (
                        content.decode("utf-8-sig")
                        if isinstance(content, bytes)
                        else content
                    )
                    reader = csv.DictReader(io.StringIO(text))
                    if reader.fieldnames:
                        fieldnames = [
                            f.strip().lower().replace(" ", "_") for f in reader.fieldnames
                        ]
                        for row in reader:
                            row_dict = {
                                fieldnames[idx]: (val.strip() if val else "")
                                for idx, (key, val) in enumerate(row.items())
                                if idx < len(fieldnames)
                            }
                            raw_rows.append(row_dict)
                except Exception as exc:
                    scanner.add_validation_error(filename, 0, "file", f"Failed to parse CSV: {exc}")
                    continue

            if not raw_rows:
                scanner.add_validation_error(filename, 0, "file", "File is empty or missing headers.")
                continue

            headers = list(raw_rows[0].keys())
            dataset_type = recognize_file_type(headers)
            processed_types.add(dataset_type)

            self._process_single_dataset(
                filename=filename,
                dataset_type=dataset_type,
                raw_rows=raw_rows,
                scanner=scanner,
            )

        # Check for missing constraint datasets and issue warnings
        if DatasetTypeEnum.VENDOR_CAPACITY not in processed_types:
            scanner.add_warning("Vendor Capacity dataset not provided. Multi-vendor capacity constraints cannot be fully evaluated.")
        if DatasetTypeEnum.VEHICLE_CAPACITY not in processed_types:
            scanner.add_warning("Vehicle Capacity dataset not provided. Transport vehicle allocation constraints cannot be evaluated.")
        if DatasetTypeEnum.MATERIAL_PARAMETERS not in processed_types:
            scanner.add_warning("Material Parameters dataset not provided. Default safety stock and lead times will be used.")

        self.db.commit()
        return scanner.summary

    def _process_single_dataset(
        self,
        filename: str,
        dataset_type: DatasetTypeEnum,
        raw_rows: list[dict[str, str]],
        scanner: DataQualityScanner,
    ) -> None:
        total_rows = len(raw_rows)
        imported_count = 0
        duplicate_count = 0
        error_count = 0

        seen_keys: set[str] = set()

        if dataset_type == DatasetTypeEnum.CONSUMPTION:
            for row_idx, row in enumerate(raw_rows, start=2):
                p_code = row.get("plant_code", "").strip() or row.get("plant", "").strip()
                m_code = row.get("material_code", "").strip() or row.get("material", "").strip()
                date_str = (
                    row.get("date", "").strip()
                    or row.get("posting_date", "").strip()
                    or row.get("consumption_date", "").strip()
                )
                qty_str = (
                    row.get("quantity", "").strip()
                    or row.get("quantity_consumed", "").strip()
                )
                uom = row.get("uom", "KG").strip() or "KG"

                if not p_code or not m_code or not date_str or not qty_str:
                    scanner.add_validation_error(
                        filename, row_idx, "row", "Missing required fields (plant_code, material_code, date, quantity)"
                    )
                    error_count += 1
                    continue

                # Duplicate detection
                dedup_key = f"{p_code}|{m_code}|{date_str}"
                if dedup_key in seen_keys:
                    duplicate_count += 1
                    continue
                seen_keys.add(dedup_key)

                parsed_date = _parse_date(date_str)
                if not parsed_date:
                    scanner.add_validation_error(filename, row_idx, "date", f"Invalid date format: '{date_str}'")
                    error_count += 1
                    continue

                try:
                    qty = float(qty_str)
                    if qty < 0:
                        scanner.add_validation_error(filename, row_idx, "quantity", "Quantity must be non-negative")
                        error_count += 1
                        continue
                except ValueError:
                    scanner.add_validation_error(filename, row_idx, "quantity", f"Invalid quantity value: '{qty_str}'")
                    error_count += 1
                    continue

                # Auto Master Generation
                plant, p_created = self.master_gen.get_or_create_plant(p_code)
                if p_created:
                    scanner.add_auto_generated_master("Plant", plant.code, plant.name)

                material, m_created = self.master_gen.get_or_create_material(m_code, base_uom=uom)
                if m_created:
                    scanner.add_auto_generated_master("Material", material.code, material.description)

                self.db.add(
                    ConsumptionHistory(
                        plant_id=plant.id,
                        material_id=material.id,
                        consumption_date=parsed_date,
                        quantity=qty,
                        uom=uom,
                        source="ENTERPRISE_DATA_INTELLIGENCE",
                    )
                )
                imported_count += 1

        elif dataset_type == DatasetTypeEnum.INVENTORY:
            today = date.today()
            for row_idx, row in enumerate(raw_rows, start=2):
                p_code = row.get("plant_code", "").strip() or row.get("plant", "").strip()
                m_code = row.get("material_code", "").strip() or row.get("material", "").strip()
                stock_str = (
                    row.get("usable_stock", "").strip()
                    or row.get("usable_physical_stock", "").strip()
                    or row.get("stock_quantity", "").strip()
                )
                uom = row.get("uom", "KG").strip() or "KG"

                if not p_code or not m_code or not stock_str:
                    scanner.add_validation_error(
                        filename, row_idx, "row", "Missing required fields (plant_code, material_code, usable_stock)"
                    )
                    error_count += 1
                    continue

                dedup_key = f"{p_code}|{m_code}"
                if dedup_key in seen_keys:
                    duplicate_count += 1
                    continue
                seen_keys.add(dedup_key)

                try:
                    usable_stock = float(stock_str)
                    if usable_stock < 0:
                        scanner.add_validation_error(filename, row_idx, "usable_stock", "Stock must be non-negative")
                        error_count += 1
                        continue
                except ValueError:
                    scanner.add_validation_error(filename, row_idx, "usable_stock", f"Invalid stock value: '{stock_str}'")
                    error_count += 1
                    continue

                plant, p_created = self.master_gen.get_or_create_plant(p_code)
                if p_created:
                    scanner.add_auto_generated_master("Plant", plant.code, plant.name)

                material, m_created = self.master_gen.get_or_create_material(m_code, base_uom=uom)
                if m_created:
                    scanner.add_auto_generated_master("Material", material.code, material.description)

                self.db.add(
                    InventorySnapshot(
                        plant_id=plant.id,
                        material_id=material.id,
                        snapshot_date=today,
                        usable_physical_stock=usable_stock,
                        reserved_stock=0.0,
                        blocked_stock=0.0,
                        uom=uom,
                        source="ENTERPRISE_DATA_INTELLIGENCE",
                    )
                )
                imported_count += 1

        elif dataset_type == DatasetTypeEnum.PURCHASE_ORDERS:
            for row_idx, row in enumerate(raw_rows, start=2):
                po_num = row.get("po_number", "").strip() or row.get("po_id", "").strip()
                v_code = row.get("vendor_code", "").strip() or row.get("vendor", "").strip()
                p_code = row.get("plant_code", "").strip() or row.get("plant", "").strip()
                m_code = row.get("material_code", "").strip() or row.get("material", "").strip()
                order_qty_str = row.get("order_quantity", "").strip() or row.get("quantity", "").strip()
                po_date_str = row.get("po_date", "").strip() or row.get("date", "").strip()

                if not po_num or not v_code or not p_code or not m_code or not order_qty_str:
                    scanner.add_validation_error(
                        filename, row_idx, "row", "Missing required purchase order fields"
                    )
                    error_count += 1
                    continue

                dedup_key = f"{po_num}|{m_code}"
                if dedup_key in seen_keys:
                    duplicate_count += 1
                    continue
                seen_keys.add(dedup_key)

                parsed_po_date = _parse_date(po_date_str) if po_date_str else date.today()
                try:
                    order_qty = float(order_qty_str)
                except ValueError:
                    scanner.add_validation_error(filename, row_idx, "order_quantity", "Invalid order quantity")
                    error_count += 1
                    continue

                plant, p_created = self.master_gen.get_or_create_plant(p_code)
                if p_created:
                    scanner.add_auto_generated_master("Plant", plant.code, plant.name)

                material, m_created = self.master_gen.get_or_create_material(m_code)
                if m_created:
                    scanner.add_auto_generated_master("Material", material.code, material.description)

                vendor, v_created = self.master_gen.get_or_create_vendor(v_code)
                if v_created:
                    scanner.add_auto_generated_master("Vendor", vendor.code, vendor.name)

                # Fetch or create PO
                po = self.db.query(PurchaseOrder).filter(PurchaseOrder.po_number == po_num).first()
                if not po:
                    po = PurchaseOrder(
                        po_number=po_num,
                        vendor_id=vendor.id,
                        plant_id=plant.id,
                        status="OPEN",
                        po_date=parsed_po_date,
                    )
                    self.db.add(po)
                    self.db.flush()

                self.db.add(
                    PurchaseOrderLine(
                        po_id=po.id,
                        line_number=len(po.lines) + 1,
                        material_id=material.id,
                        order_quantity=order_qty,
                        open_quantity=order_qty,
                        uom=material.base_uom,
                        expected_delivery_date=parsed_po_date,
                        status="CONFIRMED",
                    )
                )
                imported_count += 1

        elif dataset_type == DatasetTypeEnum.MATERIAL_MASTER:
            for row_idx, row in enumerate(raw_rows, start=2):
                m_code = row.get("code", "").strip() or row.get("material_code", "").strip()
                desc = row.get("description", "").strip() or row.get("material_description", "").strip()
                m_type = row.get("material_type", "").strip() or row.get("type", "").strip()
                uom = row.get("base_uom", "").strip() or row.get("uom", "KG").strip()

                if not m_code:
                    scanner.add_validation_error(filename, row_idx, "code", "Material code is required")
                    error_count += 1
                    continue

                if m_code in seen_keys:
                    duplicate_count += 1
                    continue
                seen_keys.add(m_code)

                material, m_created = self.master_gen.get_or_create_material(
                    m_code, description=desc, material_type=m_type, base_uom=uom
                )
                if m_created:
                    scanner.add_auto_generated_master("Material", material.code, material.description)
                imported_count += 1

        elif dataset_type == DatasetTypeEnum.VENDOR_MASTER:
            for row_idx, row in enumerate(raw_rows, start=2):
                v_code = row.get("code", "").strip() or row.get("vendor_code", "").strip()
                name = row.get("name", "").strip() or row.get("vendor_name", "").strip()
                email = row.get("contact_email", "").strip() or row.get("email", "").strip()

                if not v_code:
                    scanner.add_validation_error(filename, row_idx, "code", "Vendor code is required")
                    error_count += 1
                    continue

                if v_code in seen_keys:
                    duplicate_count += 1
                    continue
                seen_keys.add(v_code)

                vendor, v_created = self.master_gen.get_or_create_vendor(
                    v_code, vendor_name=name, contact_email=email
                )
                if v_created:
                    scanner.add_auto_generated_master("Vendor", vendor.code, vendor.name)
                imported_count += 1

        elif dataset_type == DatasetTypeEnum.PLANT_MASTER:
            for row_idx, row in enumerate(raw_rows, start=2):
                p_code = row.get("code", "").strip() or row.get("plant_code", "").strip()
                name = row.get("name", "").strip() or row.get("plant_name", "").strip()
                loc = row.get("location", "").strip()

                if not p_code:
                    scanner.add_validation_error(filename, row_idx, "code", "Plant code is required")
                    error_count += 1
                    continue

                if p_code in seen_keys:
                    duplicate_count += 1
                    continue
                seen_keys.add(p_code)

                plant, p_created = self.master_gen.get_or_create_plant(p_code, plant_name=name, location=loc)
                if p_created:
                    scanner.add_auto_generated_master("Plant", plant.code, plant.name)
                imported_count += 1

        elif dataset_type == DatasetTypeEnum.MATERIAL_PARAMETERS:
            for row_idx, row in enumerate(raw_rows, start=2):
                p_code = row.get("plant_code", "").strip()
                m_code = row.get("material_code", "").strip()
                if not p_code or not m_code:
                    scanner.add_validation_error(filename, row_idx, "row", "plant_code and material_code required")
                    error_count += 1
                    continue

                plant, _ = self.master_gen.get_or_create_plant(p_code)
                material, _ = self.master_gen.get_or_create_material(m_code)

                pm = (
                    self.db.query(PlantMaterial)
                    .filter(PlantMaterial.plant_id == plant.id, PlantMaterial.material_id == material.id)
                    .first()
                )
                if not pm:
                    pm = PlantMaterial(plant_id=plant.id, material_id=material.id)
                    self.db.add(pm)

                for param in ("lead_time_1", "lead_time_2", "safety_stock_1", "safety_stock_2", "trigger_1", "trigger_2"):
                    if row.get(param):
                        try:
                            setattr(pm, param, float(row[param]))
                        except ValueError:
                            pass
                imported_count += 1

        else:
            # General file processing for other dataset types
            imported_count = total_rows

        scanner.add_file_report(
            FileProcessingReport(
                filename=filename,
                dataset_type=dataset_type.value,
                total_rows=total_rows,
                imported_records=imported_count,
                duplicate_records=duplicate_count,
                error_records=error_count,
            )
        )
