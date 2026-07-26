from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.domain import (
    ConsumptionHistory,
    InventorySnapshot,
    Material,
    Plant,
    PlantMaterial,
    PurchaseOrder,
    PurchaseOrderLine,
    Vendor,
)


def test_create_plant_and_material(db_session: Session) -> None:
    plant = Plant(code="PLANT-1000", name="Test Factory", location="Test Region")
    material = Material(
        code="MAT-1001",
        description="Test Polymer",
        material_type="RAW_MATERIAL",
        base_uom="KG",
    )
    db_session.add_all([plant, material])
    db_session.commit()

    assert plant.id is not None
    assert material.id is not None

    pm = PlantMaterial(
        plant_id=plant.id,
        material_id=material.id,
        abc_class="A",
        service_level_z=2.05,
        review_period_days=7,
        lead_time_days=10.0,
    )
    db_session.add(pm)
    db_session.commit()

    assert pm.id is not None
    assert pm.plant.code == "PLANT-1000"
    assert pm.material.code == "MAT-1001"


def test_plant_material_unique_constraint(db_session: Session) -> None:
    plant = Plant(code="PLANT-1", name="Plant 1")
    material = Material(code="MAT-1", description="Mat 1", base_uom="KG")
    db_session.add_all([plant, material])
    db_session.commit()

    pm1 = PlantMaterial(
        plant_id=plant.id, material_id=material.id, abc_class="B", lead_time_days=5.0
    )
    db_session.add(pm1)
    db_session.commit()

    pm2 = PlantMaterial(
        plant_id=plant.id, material_id=material.id, abc_class="C", lead_time_days=7.0
    )
    db_session.add(pm2)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_consumption_and_inventory_snapshots(db_session: Session) -> None:
    plant = Plant(code="PLANT-2", name="Plant 2")
    material = Material(code="MAT-2", description="Mat 2", base_uom="KG")
    db_session.add_all([plant, material])
    db_session.commit()

    c_rec = ConsumptionHistory(
        plant_id=plant.id,
        material_id=material.id,
        consumption_date=date(2026, 7, 20),
        quantity=150.0,
        uom="KG",
        source="SAP_MB51",
    )
    inv_rec = InventorySnapshot(
        plant_id=plant.id,
        material_id=material.id,
        snapshot_date=date(2026, 7, 20),
        usable_physical_stock=500.0,
        reserved_stock=50.0,
        blocked_stock=0.0,
        uom="KG",
        source="SAP_MB5B",
    )
    db_session.add_all([c_rec, inv_rec])
    db_session.commit()

    assert c_rec.id is not None
    assert inv_rec.id is not None
    assert inv_rec.usable_physical_stock == 500.0


def test_purchase_order_relationships(db_session: Session) -> None:
    plant = Plant(code="PLANT-3", name="Plant 3")
    material = Material(code="MAT-3", description="Mat 3", base_uom="PCS")
    vendor = Vendor(code="VEND-1", name="Vendor 1")
    db_session.add_all([plant, material, vendor])
    db_session.commit()

    po = PurchaseOrder(
        po_number="PO-100",
        vendor_id=vendor.id,
        plant_id=plant.id,
        status="OPEN",
        po_date=date(2026, 7, 15),
    )
    db_session.add(po)
    db_session.commit()

    line = PurchaseOrderLine(
        po_id=po.id,
        line_number=1,
        material_id=material.id,
        order_quantity=100.0,
        open_quantity=100.0,
        uom="PCS",
        expected_delivery_date=date(2026, 7, 25),
        status="CONFIRMED",
    )
    db_session.add(line)
    db_session.commit()

    assert len(po.lines) == 1
    assert po.lines[0].material.code == "MAT-3"
