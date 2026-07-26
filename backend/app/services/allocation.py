from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models.audit import AuditLog
from app.db.models.domain import (
    Allocation,
    AllocationStatusEnum,
    Material,
    Plant,
    Vendor,
)
from app.db.models.user import User
from app.schemas.allocation import AllocationCreateSchema, AllocationUpdateSchema
from app.services.planning.availability import calculate_planning_availability
from app.services.sap import get_sap_adapter


class AllocationError(AppError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__("ALLOCATION_ERROR", message, status_code)


class AllocationConcurrencyError(AppError):
    def __init__(self, message: str = "Allocation was modified by another transaction.") -> None:
        super().__init__("CONCURRENCY_CONFLICT", message, 409)


def create_allocation(
    db: Session,
    schema: AllocationCreateSchema,
    creator_user: User,
) -> Allocation:
    plant = db.query(Plant).filter(Plant.code == schema.plant_code).first()
    if not plant:
        raise AllocationError(f"Plant with code '{schema.plant_code}' not found.", 404)

    material = db.query(Material).filter(Material.code == schema.material_code).first()
    if not material:
        raise AllocationError(f"Material with code '{schema.material_code}' not found.", 404)

    vendor = None
    if schema.vendor_code:
        vendor = db.query(Vendor).filter(Vendor.code == schema.vendor_code).first()
        if not vendor:
            raise AllocationError(f"Vendor with code '{schema.vendor_code}' not found.", 404)

    if schema.allocated_quantity <= 0:
        raise AllocationError("Allocated quantity must be greater than zero.")

    # Validate against current Planning Availability
    avail = calculate_planning_availability(db, plant.id, material.id)
    if schema.allocated_quantity > avail.planning_availability:
        raise AllocationError(
            f"Requested allocation quantity ({schema.allocated_quantity:.1f} {schema.uom}) exceeds "
            f"effective Planning Availability ({avail.planning_availability:.1f} "
            f"{material.base_uom})."
        )

    alloc_num = f"ALC-{datetime.now().year}-{uuid4().hex[:6].upper()}"
    allocation = Allocation(
        allocation_number=alloc_num,
        plant_id=plant.id,
        material_id=material.id,
        vendor_id=vendor.id if vendor else None,
        allocated_quantity=schema.allocated_quantity,
        uom=schema.uom,
        status=AllocationStatusEnum.DRAFT.value,
        created_by_user_id=creator_user.id,
        version=1,
    )
    db.add(allocation)
    db.flush()

    audit = AuditLog(
        action="ALLOCATION_CREATED",
        resource_type="allocations",
        resource_id=str(allocation.id),
        user_id=creator_user.id,
        user_email=creator_user.email,
        details={
            "message": (
                f"Created allocation {alloc_num} for "
                f"{schema.allocated_quantity} {schema.uom}"
            )
        },

    )
    db.add(audit)
    db.commit()
    db.refresh(allocation)
    return allocation


def update_allocation(
    db: Session,
    allocation_id: int,
    schema: AllocationUpdateSchema,
    user: User,
) -> Allocation:
    allocation = db.query(Allocation).filter(Allocation.id == allocation_id).first()
    if not allocation:
        raise AllocationError(f"Allocation with ID {allocation_id} not found.", 404)

    # Optimistic concurrency protection
    if allocation.version != schema.version:
        raise AllocationConcurrencyError(
            f"Concurrency conflict: expected version {schema.version}, found {allocation.version}."
        )

    closed_statuses = [AllocationStatusEnum.APPROVED.value, AllocationStatusEnum.REJECTED.value]
    if allocation.status in closed_statuses:
        raise AllocationError(f"Cannot edit allocation in status '{allocation.status}'.")

    if schema.vendor_code:
        vendor = db.query(Vendor).filter(Vendor.code == schema.vendor_code).first()
        if not vendor:
            raise AllocationError(f"Vendor with code '{schema.vendor_code}' not found.", 404)
        allocation.vendor_id = vendor.id

    if schema.allocated_quantity is not None:
        if schema.allocated_quantity <= 0:
            raise AllocationError("Allocated quantity must be greater than zero.")

        # CRITICAL CURRENT-EDIT EXCLUSION RULE:
        # Calculate available stock excluding current allocation itself
        avail = calculate_planning_availability(
            db, allocation.plant_id, allocation.material_id, exclude_allocation_id=allocation.id
        )
        if schema.allocated_quantity > avail.planning_availability:
            raise AllocationError(
                f"Updated allocation quantity ({schema.allocated_quantity:.1f} {allocation.uom}) "
                f"exceeds available capacity ({avail.planning_availability:.1f} "
                f"{allocation.material.base_uom})."
            )
        allocation.allocated_quantity = schema.allocated_quantity

    allocation.version += 1
    db.add(allocation)

    audit = AuditLog(
        action="ALLOCATION_UPDATED",
        resource_type="allocations",
        resource_id=str(allocation.id),
        user_id=user.id,
        user_email=user.email,
        details={
            "message": (
                f"Updated allocation {allocation.allocation_number} to "
                f"{allocation.allocated_quantity} {allocation.uom}"
            )
        },
    )
    db.add(audit)
    db.commit()
    db.refresh(allocation)
    return allocation


def submit_allocation(
    db: Session,
    allocation_id: int,
    user: User,
) -> Allocation:
    allocation = db.query(Allocation).filter(Allocation.id == allocation_id).first()
    if not allocation:
        raise AllocationError(f"Allocation with ID {allocation_id} not found.", 404)

    if allocation.status != AllocationStatusEnum.DRAFT.value:
        raise AllocationError(f"Cannot submit allocation in status '{allocation.status}'.")

    # Validate availability excluding current allocation
    avail = calculate_planning_availability(
        db, allocation.plant_id, allocation.material_id, exclude_allocation_id=allocation.id
    )
    if allocation.allocated_quantity > avail.planning_availability:
        raise AllocationError(
            f"Cannot submit allocation: quantity ({allocation.allocated_quantity:.1f}) exceeds "
            f"available capacity ({avail.planning_availability:.1f})."
        )

    allocation.status = AllocationStatusEnum.PENDING_APPROVAL.value
    allocation.version += 1
    db.add(allocation)

    audit = AuditLog(
        action="ALLOCATION_SUBMITTED",
        resource_type="allocations",
        resource_id=str(allocation.id),
        user_id=user.id,
        user_email=user.email,
        details={
            "message": f"Submitted allocation {allocation.allocation_number} for manager approval."
        },
    )
    db.add(audit)
    db.commit()
    db.refresh(allocation)
    return allocation


def approve_allocation(
    db: Session,
    allocation_id: int,
    approver_user: User,
) -> Allocation:
    allocation = db.query(Allocation).filter(Allocation.id == allocation_id).first()
    if not allocation:
        raise AllocationError(f"Allocation with ID {allocation_id} not found.", 404)

    closed_statuses = [AllocationStatusEnum.APPROVED.value, AllocationStatusEnum.REJECTED.value]
    if allocation.status in closed_statuses:
        raise AllocationError(f"Cannot approve allocation in status '{allocation.status}'.")

    # Validate availability excluding current allocation if it was DRAFT
    if allocation.status == AllocationStatusEnum.DRAFT.value:
        avail = calculate_planning_availability(
            db, allocation.plant_id, allocation.material_id, exclude_allocation_id=allocation.id
        )
        if allocation.allocated_quantity > avail.planning_availability:
            raise AllocationError(
                "Cannot approve allocation: quantity exceeds available capacity."
            )

    allocation.status = AllocationStatusEnum.APPROVED.value
    allocation.approved_by_user_id = approver_user.id
    allocation.version += 1

    # Outbound SAP write-back integration
    adapter = get_sap_adapter()
    adapter.write_back_allocation(db, allocation)

    audit = AuditLog(
        action="ALLOCATION_APPROVED",
        resource_type="allocations",
        resource_id=str(allocation.id),
        user_id=approver_user.id,
        user_email=approver_user.email,
        details={
            "message": (
                f"Approved allocation {allocation.allocation_number} with SAP reference "
                f"{allocation.sap_reference_id}"
            )
        },
    )
    db.add(audit)
    db.commit()
    db.refresh(allocation)
    return allocation


def reject_allocation(
    db: Session,
    allocation_id: int,
    rejection_reason: str,
    approver_user: User,
) -> Allocation:
    allocation = db.query(Allocation).filter(Allocation.id == allocation_id).first()
    if not allocation:
        raise AllocationError(f"Allocation with ID {allocation_id} not found.", 404)

    closed_statuses = [AllocationStatusEnum.APPROVED.value, AllocationStatusEnum.REJECTED.value]
    if allocation.status in closed_statuses:
        raise AllocationError(f"Cannot reject allocation in status '{allocation.status}'.")

    allocation.status = AllocationStatusEnum.REJECTED.value
    allocation.approved_by_user_id = approver_user.id
    allocation.rejection_reason = rejection_reason
    allocation.version += 1
    db.add(allocation)

    audit = AuditLog(
        action="ALLOCATION_REJECTED",
        resource_type="allocations",
        resource_id=str(allocation.id),
        user_id=approver_user.id,
        user_email=approver_user.email,
        details={
            "message": f"Rejected allocation {allocation.allocation_number}: {rejection_reason}"
        },
    )
    db.add(audit)
    db.commit()
    db.refresh(allocation)
    return allocation
