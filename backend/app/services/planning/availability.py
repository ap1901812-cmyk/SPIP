from __future__ import annotations

from datetime import date, timedelta
from typing import NamedTuple

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.domain import (
    Allocation,
    AllocationStatusEnum,
    InventorySnapshot,
    PurchaseOrder,
    PurchaseOrderLine,
)


class AvailabilityResult(NamedTuple):
    usable_physical_stock: float
    reserved_stock_info: float
    blocked_stock_info: float
    eligible_incoming_po_qty: float
    committed_allocations: float
    planning_availability: float


def calculate_planning_availability(
    db: Session,
    plant_id: int,
    material_id: int,
    decision_horizon_days: int | None = None,
    as_of_date: date | None = None,
    exclude_allocation_id: int | None = None,
) -> AvailabilityResult:
    """Calculates Planning Availability (AI) avoiding double counting:
    AI = usable_physical_stock + eligible_incoming_po_qty - committed_allocations

    usable_physical_stock is already net of reserved & blocked inventory.
    Reserved and blocked stock are returned for audit trace only and NOT subtracted again.

    Committed allocations include active allocations in PENDING_APPROVAL or APPROVED status.
    exclude_allocation_id excludes a specific allocation (for edit validation).
    """
    horizon = (
        decision_horizon_days
        if decision_horizon_days is not None
        else get_settings().planning_decision_horizon_days
    )
    ref_date = as_of_date or date.today()
    horizon_cutoff = ref_date + timedelta(days=horizon)

    # 1. Fetch latest InventorySnapshot
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

    if latest_snapshot:
        usable_stock = float(latest_snapshot.usable_physical_stock)
        reserved_info = float(latest_snapshot.reserved_stock)
        blocked_info = float(latest_snapshot.blocked_stock)
    else:
        usable_stock = 0.0
        reserved_info = 0.0
        blocked_info = 0.0

    from sqlalchemy import or_

    # 2. Fetch eligible open purchase order supply
    po_lines = (
        db.query(PurchaseOrderLine)
        .join(PurchaseOrder)
        .filter(
            or_(PurchaseOrderLine.plant_id == plant_id, PurchaseOrder.plant_id == plant_id),
            PurchaseOrderLine.material_id == material_id,
            PurchaseOrder.status == "OPEN",
            PurchaseOrderLine.status == "CONFIRMED",
            PurchaseOrderLine.expected_delivery_date <= horizon_cutoff,
        )
        .all()
    )
    eligible_po_qty = sum(float(line.open_quantity) for line in po_lines if line.open_quantity > 0)

    # 3. Fetch active committed allocations (PENDING_APPROVAL and APPROVED)
    active_statuses = [
        AllocationStatusEnum.PENDING_APPROVAL.value,
        AllocationStatusEnum.APPROVED.value,
    ]
    query_alloc = db.query(Allocation).filter(
        Allocation.plant_id == plant_id,
        Allocation.material_id == material_id,
        Allocation.status.in_(active_statuses),
    )
    if exclude_allocation_id is not None:
        query_alloc = query_alloc.filter(Allocation.id != exclude_allocation_id)

    allocations = query_alloc.all()
    committed_allocations = sum(float(a.allocated_quantity) for a in allocations)

    # Planning Availability calculation: usable + eligible PO - committed
    effective_ai = max(0.0, usable_stock + eligible_po_qty - committed_allocations)

    return AvailabilityResult(
        usable_physical_stock=round(usable_stock, 4),
        reserved_stock_info=round(reserved_info, 4),
        blocked_stock_info=round(blocked_info, 4),
        eligible_incoming_po_qty=round(eligible_po_qty, 4),
        committed_allocations=round(committed_allocations, 4),
        planning_availability=round(effective_ai, 4),
    )
