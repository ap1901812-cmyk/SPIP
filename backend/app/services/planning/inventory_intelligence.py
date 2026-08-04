from __future__ import annotations

from datetime import date, timedelta

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.domain import (
    Allocation,
    AllocationStatusEnum,
    InventorySnapshot,
    PurchaseOrder,
    PurchaseOrderLine,
)


class InventoryIntelligenceResult(BaseModel):
    plant_id: int
    material_id: int
    usable_physical_stock: float = 0.0
    reserved_stock: float = 0.0
    blocked_stock: float = 0.0
    open_po_quantity: float = 0.0
    gate_entry_quantity: float = 0.0
    incoming_inventory: float = 0.0
    committed_allocations: float = 0.0
    planning_available_inventory: float = 0.0
    days_of_inventory: float = 999.0
    inventory_position_status: str = "BALANCED"


def analyze_inventory_intelligence(
    db: Session,
    plant_id: int,
    material_id: int,
    average_daily_demand: float = 0.0,
    decision_horizon_days: int | None = None,
    as_of_date: date | None = None,
) -> InventoryIntelligenceResult:
    """Consumes Current Stock, Open Purchase Orders, and Gate Entries to calculate

    Planning Available Inventory, Incoming Supply, and Days of Inventory (DOI).
    Executed prior to RMPM Statistical Planning Engine.
    """
    horizon = (
        decision_horizon_days
        if decision_horizon_days is not None
        else get_settings().planning_decision_horizon_days
    )
    ref_date = as_of_date or date.today()
    horizon_cutoff = ref_date + timedelta(days=horizon)

    # 1. Current Usable Physical Stock
    latest_snapshot = (
        db.query(InventorySnapshot)
        .filter(
            InventorySnapshot.plant_id == plant_id,
            InventorySnapshot.material_id == material_id,
            InventorySnapshot.snapshot_date <= ref_date,
        )
        .order_by(InventorySnapshot.snapshot_date.desc(), InventorySnapshot.id.desc())
        .first()
    )

    usable_stock = float(latest_snapshot.usable_physical_stock) if latest_snapshot else 0.0
    reserved_stock = float(latest_snapshot.reserved_stock) if latest_snapshot else 0.0
    blocked_stock = float(latest_snapshot.blocked_stock) if latest_snapshot else 0.0

    # 2. Eligible Open Purchase Order Supply
    po_lines = (
        db.query(PurchaseOrderLine)
        .join(PurchaseOrder)
        .filter(
            PurchaseOrder.plant_id == plant_id,
            PurchaseOrderLine.material_id == material_id,
            PurchaseOrder.status == "OPEN",
            PurchaseOrderLine.status == "CONFIRMED",
            PurchaseOrderLine.expected_delivery_date <= horizon_cutoff,
        )
        .all()
    )
    open_po_qty = sum(float(line.open_quantity) for line in po_lines if line.open_quantity > 0)
    gate_entry_qty = 0.0  # Open GRN / Gate Entry balance placeholder

    incoming_supply = open_po_qty + gate_entry_qty

    # 3. Active Committed Allocations
    active_statuses = [
        AllocationStatusEnum.PENDING_APPROVAL.value,
        AllocationStatusEnum.APPROVED.value,
    ]
    allocations = (
        db.query(Allocation)
        .filter(
            Allocation.plant_id == plant_id,
            Allocation.material_id == material_id,
            Allocation.status.in_(active_statuses),
        )
        .all()
    )
    committed_alloc = sum(float(a.allocated_quantity) for a in allocations)

    # Planning Available Inventory: Usable Physical Stock + Incoming Supply - Committed Allocations
    ai = max(0.0, usable_stock + incoming_supply - committed_alloc)

    # Days of Inventory (DOI)
    if average_daily_demand > 0:
        doi = round(ai / average_daily_demand, 2)
    else:
        doi = 999.0

    pos_status = "HEALTHY"
    if doi < 7.0:
        pos_status = "CRITICAL_LOW"
    elif doi < 15.0:
        pos_status = "MODERATE"
    elif doi > 90.0:
        pos_status = "SURPLUS"

    return InventoryIntelligenceResult(
        plant_id=plant_id,
        material_id=material_id,
        usable_physical_stock=round(usable_stock, 4),
        reserved_stock=round(reserved_stock, 4),
        blocked_stock=round(blocked_stock, 4),
        open_po_quantity=round(open_po_qty, 4),
        gate_entry_quantity=round(gate_entry_qty, 4),
        incoming_inventory=round(incoming_supply, 4),
        committed_allocations=round(committed_alloc, 4),
        planning_available_inventory=round(ai, 4),
        days_of_inventory=doi,
        inventory_position_status=pos_status,
    )
