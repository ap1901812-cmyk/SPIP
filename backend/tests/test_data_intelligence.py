from __future__ import annotations

import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.audit import AuditLog
from app.db.models.domain import Material, Plant, Vendor
from app.db.models.user import User
from app.services.data_intelligence.file_recognizer import DatasetTypeEnum, recognize_file_type
from app.services.data_intelligence.master_generator import AutoMasterGenerator
from app.services.data_intelligence.quality_scanner import DataQualityScanner
from app.services.data_intelligence.service import EnterpriseDataIntelligenceService


def test_file_recognizer_signatures() -> None:
    headers_consumption = ["plant_code", "material_code", "date", "quantity"]
    assert recognize_file_type(headers_consumption) == DatasetTypeEnum.CONSUMPTION

    headers_inventory = ["plant_code", "material_code", "usable_stock", "uom"]
    assert recognize_file_type(headers_inventory) == DatasetTypeEnum.INVENTORY

    headers_po = ["po_number", "vendor_code", "plant_code", "material_code", "order_quantity"]
    assert recognize_file_type(headers_po) == DatasetTypeEnum.PURCHASE_ORDERS

    headers_material = ["code", "description", "material_type", "base_uom"]
    assert recognize_file_type(headers_material) == DatasetTypeEnum.MATERIAL_MASTER

    headers_vendor = ["code", "name", "contact_email"]
    assert recognize_file_type(headers_vendor) == DatasetTypeEnum.VENDOR_MASTER

    headers_unknown = ["col1", "col2", "col3"]
    assert recognize_file_type(headers_unknown) == DatasetTypeEnum.UNKNOWN


def test_auto_master_generator_and_audit(db_session: Session) -> None:
    generator = AutoMasterGenerator(db=db_session)

    # Generate Plant
    plant, p_created = generator.get_or_create_plant("AUTO-PLANT-99")
    assert p_created is True
    assert "Auto Generated Plant" in plant.name

    # Fetch existing Plant
    plant_existing, p_created2 = generator.get_or_create_plant("AUTO-PLANT-99")
    assert p_created2 is False
    assert plant_existing.id == plant.id

    # Generate Material
    mat, m_created = generator.get_or_create_material("AUTO-MAT-99", base_uom="KG")
    assert m_created is True
    assert "Auto Generated Material" in mat.description

    # Generate Vendor
    vend, v_created = generator.get_or_create_vendor("AUTO-VEND-99")
    assert v_created is True
    assert "Auto Generated Vendor" in vend.name

    db_session.commit()

    # Verify audit logs
    audit_logs = db_session.query(AuditLog).filter(AuditLog.action.like("AUTO_GENERATE_%")).all()
    assert len(audit_logs) >= 3


def test_enterprise_data_intelligence_batch(db_session: Session) -> None:
    service = EnterpriseDataIntelligenceService(db=db_session)

    csv_consumption = (
        "plant_code,material_code,date,quantity,uom\n"
        "P100,M100,2026-08-01,150.5,KG\n"
        "P100,M100,2026-08-01,150.5,KG\n"  # Duplicate row
        "P100,M101,2026-08-02,200.0,KG\n"
    ).encode("utf-8")

    csv_po = (
        "po_number,vendor_code,plant_code,material_code,order_quantity,po_date\n"
        "PO-900,V900,P100,M100,500.0,2026-08-01\n"
    ).encode("utf-8")

    files = [
        ("consumption_data.csv", csv_consumption),
        ("purchase_orders.csv", csv_po),
    ]

    summary = service.process_batch(files)

    assert summary.success is True
    assert len(summary.files_processed) == 2
    assert summary.total_records_processed == 4
    assert summary.duplicate_records_count == 1
    assert len(summary.auto_generated_masters) >= 4  # Plant P100, Materials M100/M101, Vendor V900
    assert len(summary.warnings) >= 3  # Missing vendor capacity, vehicle capacity, material parameters


from app.core.security import create_access_token, hash_password
from app.db.models.user import RoleEnum, User, UserRole


def _seed_planner(db: Session) -> dict[str, str]:
    user = User(
        email="planner_di@example.com",
        full_name="Planner User",
        hashed_password=hash_password("Pass123!"),
        is_active=True,
    )
    user.roles.append(UserRole(role_name=RoleEnum.PLANNER.value))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user_id=user.id, email=user.email, roles=[RoleEnum.PLANNER.value])
    return {"Authorization": f"Bearer {token}"}


def test_data_intelligence_api_endpoints(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = _seed_planner(db_session)
    csv_content = (
        "plant_code,material_code,usable_stock\n"
        "P200,M200,1000.0\n"
    ).encode("utf-8")

    # 1. Test ingest-batch endpoint
    response = client.post(
        "/api/v1/data-intelligence/ingest-batch",
        headers=headers,
        files=[("files", ("inventory.csv", io.BytesIO(csv_content), "text/csv"))],
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["total_records_processed"] == 1

    # 2. Test scan-results endpoint
    response_scan = client.get(
        "/api/v1/data-intelligence/scan-results",
        headers=headers,
    )
    assert response_scan.status_code == 200
    scan_data = response_scan.json()
    assert "auto_generated_count" in scan_data
    assert "audit_logs" in scan_data
