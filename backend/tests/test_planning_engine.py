from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.db.models.domain import (
    ConsumptionHistory,
    InventorySnapshot,
    Material,
    Plant,
    PlantMaterial,
    PurchaseOrder,
    PurchaseOrderLine,
)
from app.services.planning import (
    calculate_planning_availability,
    calculate_safety_stock,
    evaluate_material_planning,
)


def _seed_planning_test_data(db: Session) -> tuple[Plant, Material, PlantMaterial]:
    plant = Plant(code="PLANT-TEST", name="Test Planning Plant")
    material = Material(code="MAT-TEST", description="Test Planning Material", base_uom="KG")
    db.add_all([plant, material])
    db.commit()

    pm = PlantMaterial(
        plant_id=plant.id,
        material_id=material.id,
        abc_class="B",
        service_level_z=1.65,
        review_period_days=7,
        lead_time_days=10.0,
        min_safety_stock=10.0,
        max_safety_stock=500.0,
    )
    db.add(pm)
    db.commit()
    return plant, material, pm


def test_safety_stock_calculation(db_session: Session) -> None:
    plant, material, pm = _seed_planning_test_data(db_session)

    # Normal formula: SS = Z * sigma_d * sqrt(LT) = 1.65 * 20.0 * sqrt(9) = 99.0
    res = calculate_safety_stock(demand_std_dev=20.0, lead_time_days=9.0, plant_material=pm)
    assert res.safety_stock == 99.0
    assert res.is_overridden is False

    # Zero variability -> falls back to min floor (10.0)
    res_zero = calculate_safety_stock(demand_std_dev=0.0, lead_time_days=9.0, plant_material=pm)
    assert res_zero.safety_stock == 10.0

    # Max ceiling check
    pm.max_safety_stock = 50.0
    res_max = calculate_safety_stock(demand_std_dev=20.0, lead_time_days=9.0, plant_material=pm)
    assert res_max.safety_stock == 50.0

    # Manual override check
    pm.safety_stock_override = 125.0
    res_override = calculate_safety_stock(
        demand_std_dev=20.0, lead_time_days=9.0, plant_material=pm
    )
    assert res_override.safety_stock == 125.0
    assert res_override.is_overridden is True


def test_planning_availability_double_subtraction_prevention(db_session: Session) -> None:
    plant, material, _ = _seed_planning_test_data(db_session)
    today = date.today()

    inv = InventorySnapshot(
        plant_id=plant.id,
        material_id=material.id,
        snapshot_date=today,
        usable_physical_stock=500.0,
        reserved_stock=100.0,
        blocked_stock=50.0,
        uom="KG",
        source="TEST",
    )
    db_session.add(inv)

    po = PurchaseOrder(
        po_number="PO-AVAIL-1",
        vendor_id=1,
        plant_id=plant.id,
        status="OPEN",
        po_date=today - timedelta(days=2),
    )
    db_session.add(po)
    db_session.commit()

    line1 = PurchaseOrderLine(
        po_id=po.id,
        line_number=1,
        material_id=material.id,
        order_quantity=200.0,
        open_quantity=200.0,
        uom="KG",
        expected_delivery_date=today + timedelta(days=5),
        status="CONFIRMED",
    )
    line2 = PurchaseOrderLine(
        po_id=po.id,
        line_number=2,
        material_id=material.id,
        order_quantity=300.0,
        open_quantity=300.0,
        uom="KG",
        expected_delivery_date=today + timedelta(days=60),
        status="CONFIRMED",
    )
    line3 = PurchaseOrderLine(
        po_id=po.id,
        line_number=3,
        material_id=material.id,
        order_quantity=400.0,
        open_quantity=400.0,
        uom="KG",
        expected_delivery_date=today + timedelta(days=5),
        status="CANCELLED",
    )
    db_session.add_all([line1, line2, line3])
    db_session.commit()

    res = calculate_planning_availability(
        db_session, plant.id, material.id, decision_horizon_days=30
    )

    # PROOF OF NO DOUBLE SUBTRACTION:
    # Usable stock = 500.0, Eligible PO = 200.0. AI = 700.0 (Reserved 100.0 NOT subtracted again!)
    assert res.usable_physical_stock == 500.0
    assert res.reserved_stock_info == 100.0
    assert res.blocked_stock_info == 50.0
    assert res.eligible_incoming_po_qty == 200.0
    assert res.planning_availability == 700.0


def test_criticality_status_boundaries(db_session: Session) -> None:
    plant, material, pm = _seed_planning_test_data(db_session)
    today = date.today()

    for i in range(5):
        db_session.add(
            ConsumptionHistory(
                plant_id=plant.id,
                material_id=material.id,
                consumption_date=today - timedelta(days=i),
                quantity=10.0,
                uom="KG",
            )
        )
    db_session.commit()

    pm.safety_stock_override = 50.0
    db_session.commit()

    # 1. AI = 80.0 < D * LT (100.0) -> CRITICAL
    db_session.add(
        InventorySnapshot(
            plant_id=plant.id,
            material_id=material.id,
            snapshot_date=today,
            usable_physical_stock=80.0,
            uom="KG",
        )
    )
    db_session.commit()
    res_crit = evaluate_material_planning(db_session, plant.code, material.code)
    assert res_crit.demand_during_lead_time == 100.0
    assert res_crit.reorder_point == 150.0
    assert res_crit.planning_availability == 80.0
    assert res_crit.criticality_status == "CRITICAL"

    # 2. AI = 100.0 == D * LT -> WARNING
    db_session.query(InventorySnapshot).update({"usable_physical_stock": 100.0})
    db_session.commit()
    res_warn_eq = evaluate_material_planning(db_session, plant.code, material.code)
    assert res_warn_eq.criticality_status == "WARNING"

    # 3. AI = 120.0 (D * LT <= AI < ROP) -> WARNING
    db_session.query(InventorySnapshot).update({"usable_physical_stock": 120.0})
    db_session.commit()
    res_warn_mid = evaluate_material_planning(db_session, plant.code, material.code)
    assert res_warn_mid.criticality_status == "WARNING"

    # 4. AI = 150.0 == ROP -> HEALTHY
    db_session.query(InventorySnapshot).update({"usable_physical_stock": 150.0})
    db_session.commit()
    res_healthy_eq = evaluate_material_planning(db_session, plant.code, material.code)
    assert res_healthy_eq.criticality_status == "HEALTHY"

    # 5. AI = 200.0 > ROP -> HEALTHY
    db_session.query(InventorySnapshot).update({"usable_physical_stock": 200.0})
    db_session.commit()
    res_healthy_above = evaluate_material_planning(db_session, plant.code, material.code)
    assert res_healthy_above.criticality_status == "HEALTHY"


def test_mathematical_traceability_reconciliation(db_session: Session) -> None:
    plant, material, pm = _seed_planning_test_data(db_session)
    res = evaluate_material_planning(db_session, plant.code, material.code)

    assert res.demand_during_lead_time == round(res.average_daily_demand * res.lead_time_days, 4)
    assert res.reorder_point == round(res.demand_during_lead_time + res.safety_stock, 4)
    assert res.planning_availability == round(
        res.usable_physical_stock + res.eligible_incoming_po_qty - res.committed_allocations, 4
    )


def test_independent_planning_configuration_parameters(db_session: Session) -> None:
    plant, material, _ = _seed_planning_test_data(db_session)
    today = date.today()

    for i in range(40):
        db_session.add(
            ConsumptionHistory(
                plant_id=plant.id,
                material_id=material.id,
                consumption_date=today - timedelta(days=i),
                quantity=10.0 if i < 10 else 50.0,
                uom="KG",
            )
        )

    po = PurchaseOrder(
        po_number="PO-CONF-TEST",
        vendor_id=1,
        plant_id=plant.id,
        status="OPEN",
        po_date=today - timedelta(days=1),
    )
    db_session.add(po)
    db_session.commit()

    line = PurchaseOrderLine(
        po_id=po.id,
        line_number=1,
        material_id=material.id,
        order_quantity=500.0,
        open_quantity=500.0,
        uom="KG",
        expected_delivery_date=today + timedelta(days=15),
        status="CONFIRMED",
    )
    db_session.add(line)
    db_session.commit()

    res_h10 = evaluate_material_planning(
        db_session, plant.code, material.code, decision_horizon_days=10
    )
    res_h20 = evaluate_material_planning(
        db_session, plant.code, material.code, decision_horizon_days=20
    )

    assert res_h10.eligible_incoming_po_qty == 0.0
    assert res_h20.eligible_incoming_po_qty == 500.0

    res_stat7 = evaluate_material_planning(
        db_session, plant.code, material.code, statistics_window_days=7
    )
    res_stat35 = evaluate_material_planning(
        db_session, plant.code, material.code, statistics_window_days=35
    )

    assert res_stat7.average_daily_demand == 10.0
    assert res_stat35.average_daily_demand > 10.0
