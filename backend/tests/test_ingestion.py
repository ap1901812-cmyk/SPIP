from __future__ import annotations

import io
import zipfile

import pytest
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models.domain import ConsumptionHistory, InventorySnapshot
from app.services.ingestion import ingest_csv_data, ingest_xlsx_data

try:
    import openpyxl
except ImportError:
    openpyxl = None


def _create_mock_xlsx_bytes(rows: list[list[str]]) -> bytes:
    if openpyxl is not None:
        wb = openpyxl.Workbook()
        ws = wb.active
        for r in rows:
            ws.append(r)
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    ct_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/sharedStrings.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
        "</Types>"
    )
    wb_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/></sheets>'
        "</workbook>"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", ct_xml)
        zf.writestr("xl/workbook.xml", wb_xml)
        ss_xml = [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        ]
        string_to_idx: dict[str, int] = {}
        for r in rows:
            for cell in r:
                if cell not in string_to_idx:
                    string_to_idx[cell] = len(string_to_idx)
                    ss_xml.append(f"<si><t>{cell}</t></si>")
        ss_xml.append("</sst>")
        zf.writestr("xl/sharedStrings.xml", "".join(ss_xml))

        sheet_xml = [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>',
        ]
        for r_idx, r in enumerate(rows, start=1):
            sheet_xml.append(f'<row r="{r_idx}">')
            for _c_idx, cell in enumerate(r, start=1):
                idx = string_to_idx[cell]
                sheet_xml.append(f'<c t="s"><v>{idx}</v></c>')
            sheet_xml.append("</row>")
        sheet_xml.append("</sheetData></worksheet>")
        zf.writestr("xl/worksheets/sheet1.xml", "".join(sheet_xml))
    return buf.getvalue()


def test_csv_consumption_ingestion_success(db_session: Session) -> None:
    csv_content = """plant_code,material_code,date,quantity,uom
PLANT-1000,MAT-1001,2026-07-20,150.5,KG
PLANT-1000,MAT-1001,2026-07-21,160.0,KG
"""
    result = ingest_csv_data(db_session, entity_type="consumption", file_content=csv_content)

    assert result.success is True
    assert result.imported_records == 2
    assert len(result.errors) == 0

    recs = db_session.query(ConsumptionHistory).all()
    assert len(recs) == 2
    assert recs[0].quantity == 150.5


def test_csv_inventory_ingestion_success(db_session: Session) -> None:
    csv_content = """plant_code,material_code,usable_stock,reserved_stock,blocked_stock,uom
PLANT-2000,MAT-2002,500.0,50.0,0.0,PCS
"""
    result = ingest_csv_data(db_session, entity_type="inventory", file_content=csv_content)

    assert result.success is True
    assert result.imported_records == 1

    inv = db_session.query(InventorySnapshot).first()
    assert inv is not None
    assert inv.usable_physical_stock == 500.0


def test_xlsx_consumption_ingestion_success(db_session: Session) -> None:
    xlsx_bytes = _create_mock_xlsx_bytes(
        [
            ["plant_code", "material_code", "date", "quantity", "uom"],
            ["PLANT-1000", "MAT-1001", "2026-07-20", "250.0", "KG"],
        ]
    )
    result = ingest_xlsx_data(db_session, entity_type="consumption", file_content=xlsx_bytes)

    assert result.success is True
    assert result.imported_records == 1

    rec = db_session.query(ConsumptionHistory).first()
    assert rec is not None
    assert rec.quantity == 250.0


def test_xlsx_corrupt_file_rejection(db_session: Session) -> None:
    corrupt_bytes = b"not a valid xlsx zip binary content"
    with pytest.raises(AppError) as exc_info:
        ingest_xlsx_data(db_session, entity_type="consumption", file_content=corrupt_bytes)
    assert exc_info.value.code == "INVALID_IMPORT_DATA"


def test_csv_ingestion_missing_header_columns(db_session: Session) -> None:
    csv_content = """wrong_header1,wrong_header2
value1,value2
"""
    with pytest.raises(AppError) as exc_info:
        ingest_csv_data(db_session, entity_type="consumption", file_content=csv_content)
    assert exc_info.value.code == "INVALID_IMPORT_DATA"


def test_csv_ingestion_invalid_row_values(db_session: Session) -> None:
    csv_content = """plant_code,material_code,date,quantity,uom
PLANT-1000,MAT-1001,invalid-date,150.5,KG
PLANT-1000,MAT-1001,2026-07-21,-50.0,KG
"""
    result = ingest_csv_data(db_session, entity_type="consumption", file_content=csv_content)

    assert result.success is False
    assert result.imported_records == 0
    assert len(result.errors) == 2
    assert result.errors[0].field == "date"
    assert result.errors[1].field == "quantity"


def test_unsupported_entity_type(db_session: Session) -> None:
    csv_content = "a,b\n1,2"
    with pytest.raises(AppError):
        ingest_csv_data(db_session, entity_type="unsupported_type", file_content=csv_content)
