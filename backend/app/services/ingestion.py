from __future__ import annotations

import csv
import io
import xml.etree.ElementTree as ET
import zipfile
from datetime import date, datetime

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models.domain import ConsumptionHistory, InventorySnapshot, Material, Plant

try:
    import openpyxl
except ImportError:
    openpyxl = None


class IngestionError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__("INVALID_IMPORT_DATA", message, 400)


class RowValidationError(BaseModel):
    row: int
    field: str
    message: str


class IngestionResult(BaseModel):
    success: bool
    entity_type: str
    imported_records: int
    total_rows: int
    errors: list[RowValidationError] = []


def _parse_date(val: str) -> date | None:
    val = val.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            pass
    return None


def _process_rows(
    db: Session,
    entity_type: str,
    raw_rows: list[dict[str, str]],
) -> IngestionResult:
    if not raw_rows:
        raise IngestionError("File contains no data rows.")

    headers = set(raw_rows[0].keys())
    errors: list[RowValidationError] = []
    imported_count = 0
    total_rows = len(raw_rows)

    if entity_type == "consumption":
        required = {"plant_code", "material_code", "date", "quantity"}
        if not required.issubset(headers):
            missing = required - headers
            raise IngestionError(f"Missing required columns: {', '.join(sorted(missing))}")

        plant_cache: dict[str, Plant] = {p.code: p for p in db.query(Plant).all()}
        material_cache: dict[str, Material] = {m.code: m for m in db.query(Material).all()}

        for row_idx, row in enumerate(raw_rows, start=2):
            p_code = row.get("plant_code", "").strip()
            m_code = row.get("material_code", "").strip()
            date_str = row.get("date", "").strip()
            qty_str = row.get("quantity", "").strip()
            uom = row.get("uom", "KG").strip() or "KG"

            if not p_code:
                errors.append(
                    RowValidationError(
                        row=row_idx, field="plant_code", message="plant_code is required"
                    )
                )
                continue
            if not m_code:
                errors.append(
                    RowValidationError(
                        row=row_idx, field="material_code", message="material_code is required"
                    )
                )
                continue

            parsed_date = _parse_date(date_str) if date_str else None
            if not parsed_date:
                errors.append(
                    RowValidationError(
                        row=row_idx, field="date", message=f"Invalid date format: '{date_str}'"
                    )
                )
                continue

            try:
                qty = float(qty_str) if qty_str else -1.0
                if qty < 0:
                    errors.append(
                        RowValidationError(
                            row=row_idx,
                            field="quantity",
                            message="Quantity must be non-negative",
                        )
                    )
                    continue
            except ValueError:
                errors.append(
                    RowValidationError(
                        row=row_idx,
                        field="quantity",
                        message=f"Invalid numeric quantity: '{qty_str}'",
                    )
                )
                continue

            plant = plant_cache.get(p_code)
            if not plant:
                plant = Plant(code=p_code, name=f"Plant {p_code}")
                db.add(plant)
                db.flush()
                plant_cache[p_code] = plant

            material = material_cache.get(m_code)
            if not material:
                material = Material(code=m_code, description=f"Material {m_code}", base_uom=uom)
                db.add(material)
                db.flush()
                material_cache[m_code] = material

            db.add(
                ConsumptionHistory(
                    plant_id=plant.id,
                    material_id=material.id,
                    consumption_date=parsed_date,
                    quantity=qty,
                    uom=uom,
                    source="EXCEL_CSV_IMPORT",
                )
            )
            imported_count += 1

    elif entity_type == "inventory":
        required = {"plant_code", "material_code", "usable_stock"}
        if not required.issubset(headers):
            missing = required - headers
            raise IngestionError(f"Missing required columns: {', '.join(sorted(missing))}")

        plant_cache = {p.code: p for p in db.query(Plant).all()}
        material_cache = {m.code: m for m in db.query(Material).all()}
        today = date.today()

        for row_idx, row in enumerate(raw_rows, start=2):
            p_code = row.get("plant_code", "").strip()
            m_code = row.get("material_code", "").strip()
            stock_str = row.get("usable_stock", "").strip()
            reserved_str = row.get("reserved_stock", "0").strip() or "0"
            blocked_str = row.get("blocked_stock", "0").strip() or "0"
            uom = row.get("uom", "KG").strip() or "KG"

            if not p_code or not m_code:
                errors.append(
                    RowValidationError(
                        row=row_idx,
                        field="plant_code/material_code",
                        message="plant_code and material_code are required",
                    )
                )
                continue

            try:
                usable_stock = float(stock_str) if stock_str else -1.0
                reserved_stock = float(reserved_str) if reserved_str else 0.0
                blocked_stock = float(blocked_str) if blocked_str else 0.0
                if usable_stock < 0 or reserved_stock < 0 or blocked_stock < 0:
                    errors.append(
                        RowValidationError(
                            row=row_idx,
                            field="usable_stock",
                            message="Stock quantities must be non-negative",
                        )
                    )
                    continue
            except ValueError:
                errors.append(
                    RowValidationError(
                        row=row_idx,
                        field="usable_stock",
                        message="Invalid numeric stock value",
                    )
                )
                continue

            plant = plant_cache.get(p_code)
            if not plant:
                plant = Plant(code=p_code, name=f"Plant {p_code}")
                db.add(plant)
                db.flush()
                plant_cache[p_code] = plant

            material = material_cache.get(m_code)
            if not material:
                material = Material(code=m_code, description=f"Material {m_code}", base_uom=uom)
                db.add(material)
                db.flush()
                material_cache[m_code] = material

            db.add(
                InventorySnapshot(
                    plant_id=plant.id,
                    material_id=material.id,
                    snapshot_date=today,
                    usable_physical_stock=usable_stock,
                    reserved_stock=reserved_stock,
                    blocked_stock=blocked_stock,
                    uom=uom,
                    source="EXCEL_CSV_IMPORT",
                )
            )
            imported_count += 1

    else:
        raise IngestionError(f"Unsupported entity_type for ingestion: '{entity_type}'")

    if errors and imported_count == 0:
        db.rollback()
        return IngestionResult(
            success=False,
            entity_type=entity_type,
            imported_records=0,
            total_rows=total_rows,
            errors=errors,
        )

    db.commit()
    return IngestionResult(
        success=True,
        entity_type=entity_type,
        imported_records=imported_count,
        total_rows=total_rows,
        errors=errors,
    )


def ingest_csv_data(
    db: Session,
    entity_type: str,
    file_content: bytes | str,
) -> IngestionResult:
    if isinstance(file_content, bytes):
        try:
            text = file_content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = file_content.decode("latin-1")
    else:
        text = file_content

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise IngestionError("CSV file is empty or missing headers.")

    fieldnames = [f.strip().lower().replace(" ", "_") for f in reader.fieldnames]
    raw_rows: list[dict[str, str]] = []

    for row in reader:
        row_dict = {
            fieldnames[idx]: (val.strip() if val else "")
            for idx, (key, val) in enumerate(row.items())
            if idx < len(fieldnames)
        }
        raw_rows.append(row_dict)

    return _process_rows(db, entity_type, raw_rows)


def _extract_xlsx_rows(file_content: bytes) -> list[dict[str, str]]:
    if openpyxl is not None:
        try:
            wb = openpyxl.load_workbook(io.BytesIO(file_content), data_only=True)
            sheet = wb.active
            if not sheet or sheet.max_row < 1:
                raise IngestionError("XLSX workbook is empty.")
            rows_iter = sheet.iter_rows(values_only=True)
            header_row = next(rows_iter, None)
            if not header_row:
                raise IngestionError("XLSX file is empty or missing headers.")
            headers = [
                str(h).strip().lower().replace(" ", "_") if h is not None else ""
                for h in header_row
            ]
            result_rows: list[dict[str, str]] = []
            for r in rows_iter:
                if not any(r):
                    continue
                row_dict: dict[str, str] = {}
                for idx, h in enumerate(headers):
                    if h:
                        val = r[idx] if idx < len(r) else ""
                        row_dict[h] = str(val).strip() if val is not None else ""
                result_rows.append(row_dict)
            return result_rows
        except IngestionError:
            raise
        except Exception as exc:
            raise IngestionError("Invalid or corrupt XLSX file.") from exc

    try:
        with zipfile.ZipFile(io.BytesIO(file_content)) as zf:
            shared_strings: list[str] = []
            if "xl/sharedStrings.xml" in zf.namelist():
                ss_tree = ET.fromstring(zf.read("xl/sharedStrings.xml"))
                ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
                for si in ss_tree.findall(".//s:si", ns):
                    t_el = si.find(".//s:t", ns)
                    shared_strings.append(t_el.text if t_el is not None and t_el.text else "")

            sheet_xml = None
            for name in zf.namelist():
                if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"):
                    sheet_xml = zf.read(name)
                    break

            if not sheet_xml:
                raise IngestionError("No worksheet found in XLSX archive.")

            tree = ET.fromstring(sheet_xml)
            ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            row_elements = tree.findall(".//s:row", ns)
            if not row_elements:
                raise IngestionError("XLSX worksheet is empty.")

            parsed_rows: list[list[str]] = []
            for r in row_elements:
                cells: list[str] = []
                for c in r.findall("s:c", ns):
                    cell_type = c.get("t")
                    val_el = c.find("s:v", ns)
                    val = val_el.text if val_el is not None and val_el.text else ""
                    if cell_type == "s" and val.isdigit():
                        idx = int(val)
                        val = shared_strings[idx] if idx < len(shared_strings) else val
                    cells.append(val)
                parsed_rows.append(cells)

            if not parsed_rows or not parsed_rows[0]:
                raise IngestionError("XLSX file is empty or missing headers.")

            headers = [h.strip().lower().replace(" ", "_") for h in parsed_rows[0]]
            result_rows = []
            for row_vals in parsed_rows[1:]:
                if not any(row_vals):
                    continue
                row_dict = {
                    headers[idx]: (row_vals[idx].strip() if idx < len(row_vals) else "")
                    for idx in range(len(headers))
                }
                result_rows.append(row_dict)
            return result_rows
    except IngestionError:
        raise
    except Exception as exc:
        raise IngestionError("Invalid or corrupt XLSX file.") from exc


def ingest_xlsx_data(
    db: Session,
    entity_type: str,
    file_content: bytes,
) -> IngestionResult:
    raw_rows = _extract_xlsx_rows(file_content)
    return _process_rows(db, entity_type, raw_rows)
