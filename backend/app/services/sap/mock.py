from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.db.models.domain import (
    BOM,
    ConsumptionHistory,
    InventorySnapshot,
    Material,
    Plant,
    PlantMaterial,
    PurchaseOrder,
    PurchaseOrderLine,
    Vendor,
)
from app.services.sap.interface import SAPAdapterInterface


class MockSAPAdapter(SAPAdapterInterface):
    """Mock SAP adapter delivering deterministic synthetic enterprise data
    for demo, testing, and multi-plant planning validation.
    """

    def fetch_plants(self) -> list[dict[str, Any]]:
        return [
            {
                "code": "PLANT-1000",
                "name": "Main Manufacturing Plant",
                "location": "North Industrial Zone",
            },
            {
                "code": "PLANT-2000",
                "name": "Secondary Assembly Plant",
                "location": "South Logistics Hub",
            },
        ]

    def fetch_materials(self) -> list[dict[str, Any]]:
        return [
            {
                "code": "FG-1001",
                "description": "Premium High-Density Container (FG)",
                "material_type": "FG",
                "base_uom": "PCS",
            },
            {
                "code": "FG-1002",
                "description": "Standard Industrial Crate (FG)",
                "material_type": "FG",
                "base_uom": "PCS",
            },
            {
                "code": "MAT-1001",
                "description": "High Density Polyethylene Resin",
                "material_type": "RM",
                "base_uom": "KG",
            },
            {
                "code": "MAT-1002",
                "description": "Polypropylene Compound White",
                "material_type": "RM",
                "base_uom": "KG",
            },
            {
                "code": "MAT-2001",
                "description": "Barrier Packaging Film 50m",
                "material_type": "PM",
                "base_uom": "ROLL",
            },
            {
                "code": "MAT-2002",
                "description": "Corrugated Shipping Master Case",
                "material_type": "PM",
                "base_uom": "PCS",
            },
            {
                "code": "MAT-3001",
                "description": "Chemical Stabilizer Additive",
                "material_type": "RM",
                "base_uom": "L",
            },
        ]

    def fetch_vendors(self) -> list[dict[str, Any]]:
        return [
            {
                "code": "VEND-5001",
                "name": "Global Polymers Corp",
                "contact_email": "orders@globalpolymers.test",
                "is_active": True,
            },
            {
                "code": "VEND-5002",
                "name": "Apex Packaging Supplies",
                "contact_email": "sales@apexpack.test",
                "is_active": True,
            },
            {
                "code": "VEND-5003",
                "name": "Specialty Chemicals Ltd",
                "contact_email": "supply@spec-chem.test",
                "is_active": True,
            },
        ]

    def fetch_consumption(self, plant_code: str | None = None) -> list[dict[str, Any]]:
        today = date.today()
        records: list[dict[str, Any]] = []
        plants = (
            [plant_code]
            if plant_code
            else ["PLANT-1000", "PLANT-2000"]
        )

        base_quantities = {
            ("PLANT-1000", "MAT-1001"): 120.0,
            ("PLANT-1000", "MAT-1002"): 85.0,
            ("PLANT-1000", "MAT-2001"): 45.0,
            ("PLANT-2000", "MAT-2002"): 150.0,
            ("PLANT-2000", "MAT-3001"): 30.0,
        }

        uoms = {
            "MAT-1001": "KG",
            "MAT-1002": "KG",
            "MAT-2001": "ROLL",
            "MAT-2002": "PCS",
            "MAT-3001": "L",
        }

        for day_offset in range(30, 0, -1):
            obs_date = today - timedelta(days=day_offset)
            for p_code in plants:
                for mat_code, base_qty in [
                    ("MAT-1001", 120.0),
                    ("MAT-1002", 85.0),
                    ("MAT-2001", 45.0),
                    ("MAT-2002", 150.0),
                    ("MAT-3001", 30.0),
                ]:
                    if (p_code, mat_code) in base_quantities:
                        # Deterministic variation without random
                        variance = ((day_offset * 7 + ord(mat_code[-1])) % 21) - 10
                        qty = max(5.0, base_qty + variance)
                        records.append(
                            {
                                "plant_code": p_code,
                                "material_code": mat_code,
                                "consumption_date": obs_date,
                                "quantity": float(qty),
                                "uom": uoms[mat_code],
                                "source": "SAP_MB51",
                            }
                        )
        return records

    def fetch_inventory(self, plant_code: str | None = None) -> list[dict[str, Any]]:
        today = date.today()
        all_snapshots = [
            {
                "plant_code": "PLANT-1000",
                "material_code": "MAT-1001",
                "snapshot_date": today,
                "usable_physical_stock": 850.0,
                "reserved_stock": 100.0,
                "blocked_stock": 0.0,
                "uom": "KG",
                "source": "SAP_MB5B",
            },
            {
                "plant_code": "PLANT-1000",
                "material_code": "MAT-1002",
                "snapshot_date": today,
                "usable_physical_stock": 420.0,
                "reserved_stock": 50.0,
                "blocked_stock": 20.0,
                "uom": "KG",
                "source": "SAP_MB5B",
            },
            {
                "plant_code": "PLANT-1000",
                "material_code": "MAT-2001",
                "snapshot_date": today,
                "usable_physical_stock": 180.0,
                "reserved_stock": 20.0,
                "blocked_stock": 0.0,
                "uom": "ROLL",
                "source": "SAP_MB5B",
            },
            {
                "plant_code": "PLANT-2000",
                "material_code": "MAT-2002",
                "snapshot_date": today,
                "usable_physical_stock": 1100.0,
                "reserved_stock": 200.0,
                "blocked_stock": 50.0,
                "uom": "PCS",
                "source": "SAP_MB5B",
            },
            {
                "plant_code": "PLANT-2000",
                "material_code": "MAT-3001",
                "snapshot_date": today,
                "usable_physical_stock": 95.0,
                "reserved_stock": 10.0,
                "blocked_stock": 0.0,
                "uom": "L",
                "source": "SAP_MB5B",
            },
        ]
        if plant_code:
            return [s for s in all_snapshots if s["plant_code"] == plant_code]
        return all_snapshots

    def fetch_purchase_orders(self, plant_code: str | None = None) -> list[dict[str, Any]]:
        today = date.today()
        pos = [
            {
                "po_number": "PO-90001",
                "vendor_code": "VEND-5001",
                "plant_code": "PLANT-1000",
                "status": "OPEN",
                "po_date": today - timedelta(days=5),
                "lines": [
                    {
                        "line_number": 1,
                        "material_code": "MAT-1001",
                        "order_quantity": 500.0,
                        "open_quantity": 500.0,
                        "uom": "KG",
                        "expected_delivery_date": today + timedelta(days=3),
                        "status": "CONFIRMED",
                    }
                ],
            },
            {
                "po_number": "PO-90002",
                "vendor_code": "VEND-5002",
                "plant_code": "PLANT-2000",
                "status": "OPEN",
                "po_date": today - timedelta(days=2),
                "lines": [
                    {
                        "line_number": 1,
                        "material_code": "MAT-2002",
                        "order_quantity": 1000.0,
                        "open_quantity": 1000.0,
                        "uom": "PCS",
                        "expected_delivery_date": today + timedelta(days=5),
                        "status": "CONFIRMED",
                    }
                ],
            },
        ]
        if plant_code:
            return [p for p in pos if p["plant_code"] == plant_code]
        return pos

    def sync_to_database(self, db: Session) -> dict[str, int]:
        counts = {
            "plants": 0,
            "materials": 0,
            "vendors": 0,
            "consumption": 0,
            "inventory": 0,
            "purchase_orders": 0,
        }

        # 1. Sync Plants
        plant_map: dict[str, Plant] = {}
        for p_data in self.fetch_plants():
            plant = db.query(Plant).filter(Plant.code == p_data["code"]).first()
            if not plant:
                plant = Plant(
                    code=p_data["code"], name=p_data["name"], location=p_data["location"]
                )
                db.add(plant)
                db.flush()
                counts["plants"] += 1
            plant_map[plant.code] = plant

        # 2. Sync Materials
        material_map: dict[str, Material] = {}
        for m_data in self.fetch_materials():
            mat = db.query(Material).filter(Material.code == m_data["code"]).first()
            if not mat:
                mat = Material(
                    code=m_data["code"],
                    description=m_data["description"],
                    material_type=m_data["material_type"],
                    base_uom=m_data["base_uom"],
                )
                db.add(mat)
                db.flush()
                counts["materials"] += 1
            material_map[mat.code] = mat

        # 3. Sync Vendors
        vendor_map: dict[str, Vendor] = {}
        for v_data in self.fetch_vendors():
            vendor = db.query(Vendor).filter(Vendor.code == v_data["code"]).first()
            if not vendor:
                vendor = Vendor(
                    code=v_data["code"],
                    name=v_data["name"],
                    contact_email=v_data.get("contact_email"),
                    is_active=v_data.get("is_active", True),
                )
                db.add(vendor)
                db.flush()
                counts["vendors"] += 1
            vendor_map[vendor.code] = vendor

        # Setup PlantMaterials default config
        for plant in plant_map.values():
            for mat in material_map.values():
                pm = (
                    db.query(PlantMaterial)
                    .filter(
                        PlantMaterial.plant_id == plant.id, PlantMaterial.material_id == mat.id
                    )
                    .first()
                )
                if not pm:
                    db.add(
                        PlantMaterial(
                            plant_id=plant.id,
                            material_id=mat.id,
                            abc_class="B",
                            service_level_z=1.65,
                            review_period_days=7,
                            min_safety_stock=0.0,
                            lead_time_1=7.0,
                            lead_time_2=3.0,
                            safety_stock_1=100.0,
                            safety_stock_2=50.0,
                            trigger_1=200.0,
                            trigger_2=100.0,
                        )
                    )

        # 4. Sync Consumption
        for c_data in self.fetch_consumption():
            plant = plant_map.get(c_data["plant_code"])
            mat = material_map.get(c_data["material_code"])
            if plant and mat:
                exists = (
                    db.query(ConsumptionHistory)
                    .filter(
                        ConsumptionHistory.plant_id == plant.id,
                        ConsumptionHistory.material_id == mat.id,
                        ConsumptionHistory.consumption_date == c_data["consumption_date"],
                    )
                    .first()
                )
                if not exists:
                    db.add(
                        ConsumptionHistory(
                            plant_id=plant.id,
                            material_id=mat.id,
                            consumption_date=c_data["consumption_date"],
                            quantity=c_data["quantity"],
                            uom=c_data["uom"],
                            source=c_data["source"],
                        )
                    )
                    counts["consumption"] += 1

        # 5. Sync Inventory
        for i_data in self.fetch_inventory():
            plant = plant_map.get(i_data["plant_code"])
            mat = material_map.get(i_data["material_code"])
            if plant and mat:
                exists = (
                    db.query(InventorySnapshot)
                    .filter(
                        InventorySnapshot.plant_id == plant.id,
                        InventorySnapshot.material_id == mat.id,
                        InventorySnapshot.snapshot_date == i_data["snapshot_date"],
                    )
                    .first()
                )
                if not exists:
                    db.add(
                        InventorySnapshot(
                            plant_id=plant.id,
                            material_id=mat.id,
                            snapshot_date=i_data["snapshot_date"],
                            usable_physical_stock=i_data["usable_physical_stock"],
                            reserved_stock=i_data["reserved_stock"],
                            blocked_stock=i_data["blocked_stock"],
                            uom=i_data["uom"],
                            source=i_data["source"],
                        )
                    )
                    counts["inventory"] += 1

        # 6. Sync Purchase Orders
        for po_data in self.fetch_purchase_orders():
            plant = plant_map.get(po_data["plant_code"])
            vendor = vendor_map.get(po_data["vendor_code"])
            if plant and vendor:
                po = (
                    db.query(PurchaseOrder)
                    .filter(PurchaseOrder.po_number == po_data["po_number"])
                    .first()
                )
                if not po:
                    po = PurchaseOrder(
                        po_number=po_data["po_number"],
                        vendor_id=vendor.id,
                        plant_id=plant.id,
                        status=po_data["status"],
                        po_date=po_data["po_date"],
                    )
                    db.add(po)
                    db.flush()
                    counts["purchase_orders"] += 1

                    for line in po_data.get("lines", []):
                        mat = material_map.get(line["material_code"])
                        if mat:
                            db.add(
                                PurchaseOrderLine(
                                    po_id=po.id,
                                    line_number=line["line_number"],
                                    material_id=mat.id,
                                    order_quantity=line["order_quantity"],
                                    open_quantity=line["open_quantity"],
                                    uom=line["uom"],
                                    expected_delivery_date=line["expected_delivery_date"],
                                    status=line["status"],
                                )
                            )

        # 7. Sync BOMs
        counts["boms"] = 0
        fg1 = material_map.get("FG-1001")
        fg2 = material_map.get("FG-1002")
        mat1001 = material_map.get("MAT-1001")
        mat2001 = material_map.get("MAT-2001")
        mat1002 = material_map.get("MAT-1002")
        mat2002 = material_map.get("MAT-2002")

        bom_specs = [
            (fg1, mat1001, 2.5, "KG"),
            (fg1, mat2001, 1.0, "ROLL"),
            (fg2, mat1002, 3.0, "KG"),
            (fg2, mat2002, 1.0, "PCS"),
        ]

        for fg_mat, comp_mat, qty, uom in bom_specs:
            if fg_mat and comp_mat:
                existing_bom = (
                    db.query(BOM)
                    .filter(BOM.fg_material_id == fg_mat.id, BOM.component_material_id == comp_mat.id)
                    .first()
                )
                if not existing_bom:
                    db.add(
                        BOM(
                            fg_material_id=fg_mat.id,
                            component_material_id=comp_mat.id,
                            required_quantity=qty,
                            unit_of_measure=uom,
                            is_active=True,
                        )
                    )
                    counts["boms"] += 1

        db.commit()
        return counts

    def write_back_allocation(self, db: Session, allocation: Any) -> dict[str, Any]:
        """Simulates SAP write-back for approved allocation in demo mode."""
        sap_ref = f"SAP-PO-9000{allocation.id}"
        allocation.sap_reference_id = sap_ref
        db.add(allocation)
        db.commit()
        return {
            "status": "SUCCESS",
            "sap_reference_id": sap_ref,
            "message": f"Allocation {allocation.allocation_number} committed to SAP mock adapter.",
        }
