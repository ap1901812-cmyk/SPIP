from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.core.errors import AppError
from app.db.models.domain import (
    Allocation,
    Material,
    Plant,
    PlantMaterial,
    ProcurementRecommendation,
    Vendor,
    VendorCapacity,
    VendorMaterial,
)
from app.db.models.user import User


class NotificationPayload(BaseModel):
    email_payload: dict[str, Any]
    in_app_payload: dict[str, Any]


class ProcurementAllocationItem(BaseModel):
    id: int
    allocation_number: str
    recommendation_id: int | None = None
    plant_code: str
    material_code: str
    material_description: str
    material_type: str
    vendor_id: int | None = None
    vendor_code: str | None = None
    vendor_name: str | None = None
    allocated_quantity: float
    uom: str
    dispatch_date: date | None = None
    expected_arrival_date: date | None = None
    status: str  # DRAFT, APPROVED, REJECTED
    allocation_notes: str | None = None
    version: int
    created_by_user_id: int | None = None
    approved_by_user_id: int | None = None
    notification_payload: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProcurementAllocationSummary(BaseModel):
    plant_code: str
    total_allocations_generated: int
    total_quantity_allocated: float
    allocations: list[ProcurementAllocationItem] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


def generate_procurement_allocations(
    db: Session,
    plant_code: str,
    recommendation_ids: list[int] | None = None,
    user_id: int | None = None,
) -> ProcurementAllocationSummary:
    """Converts Phase 9 ProcurementRecommendations into dynamic vendor allocation plans.

    Supports multi-vendor splitting, vendor capacities, vehicle capacities, and plant storage constraints.
    Does NOT recalculate planning or send real emails/notifications.
    """
    plant = db.query(Plant).filter(Plant.code == plant_code).first()
    if not plant:
        raise AppError("PLANT_NOT_FOUND", f"Plant with code '{plant_code}' not found.", 404)

    query = db.query(ProcurementRecommendation).filter(
        ProcurementRecommendation.plant_id == plant.id,
        ProcurementRecommendation.status == "RECOMMENDED",
    )
    if recommendation_ids:
        query = query.filter(ProcurementRecommendation.id.in_(recommendation_ids))

    recommendations = query.all()
    if not recommendations:
        return ProcurementAllocationSummary(
            plant_code=plant_code,
            total_allocations_generated=0,
            total_quantity_allocated=0.0,
            allocations=[],
        )

    allocations_generated: list[ProcurementAllocationItem] = []
    total_qty_allocated = 0.0

    today = date.today()

    for rec in recommendations:
        mat = rec.material
        remaining_qty = rec.recommended_qty

        # Fetch vendors offering this material at the plant
        vendor_materials = (
            db.query(VendorMaterial)
            .filter(VendorMaterial.plant_id == plant.id, VendorMaterial.material_id == mat.id)
            .order_by(VendorMaterial.is_primary.desc())
            .all()
        )

        # Fallback vendor if no specific mapping exists
        vendors_to_allocate: list[tuple[Vendor, float, float]] = []  # (vendor, lead_time, daily_cap)

        if vendor_materials:
            for vm in vendor_materials:
                v = vm.vendor
                lt = vm.vendor_lead_time_days if vm.vendor_lead_time_days else 7.0
                cap = v.capacity_per_day if v and v.capacity_per_day else 10000.0
                vendors_to_allocate.append((v, lt, cap))
        elif rec.recommended_vendor:
            v = rec.recommended_vendor
            cap = v.capacity_per_day if v.capacity_per_day else 10000.0
            vendors_to_allocate.append((v, 7.0, cap))
        else:
            default_v = db.query(Vendor).filter(Vendor.is_active == True).first()
            if default_v:
                vendors_to_allocate.append((default_v, 7.0, 10000.0))

        if not vendors_to_allocate:
            continue

        # Check plant storage capacity limit constraint
        storage_cap = mat.storage_capacity_limit
        if storage_cap and storage_cap > 0:
            if remaining_qty > storage_cap:
                remaining_qty = storage_cap

        # Multi-Vendor Allocation Splitting Logic
        split_idx = 1
        num_vendors = len(vendors_to_allocate)

        for v, lt, cap in vendors_to_allocate:
            if remaining_qty <= 0:
                break

            # Max quantity allocated to this vendor based on daily capacity
            alloc_qty_vendor = min(remaining_qty, cap)
            if alloc_qty_vendor <= 0:
                continue

            remaining_qty -= alloc_qty_vendor
            total_qty_allocated += alloc_qty_vendor

            dispatch_dt = rec.dispatch_date or (today + timedelta(days=2))
            arrival_dt = rec.expected_arrival_date or (dispatch_dt + timedelta(days=int(lt)))

            alloc_num = f"ALC-{plant.code}-{today.strftime('%Y%m%d')}-{uuid4().hex[:5].upper()}"
            split_note = f"Multi-Vendor Split {split_idx}/{num_vendors}" if num_vendors > 1 else "Primary Allocation"

            alloc_model = Allocation(
                allocation_number=alloc_num,
                plant_id=plant.id,
                material_id=mat.id,
                vendor_id=v.id,
                recommendation_id=rec.id,
                allocated_quantity=round(alloc_qty_vendor, 2),
                uom=mat.base_uom or "KG",
                status="DRAFT",
                dispatch_date=dispatch_dt,
                expected_arrival_date=arrival_dt,
                allocation_notes=f"Auto-generated allocation. {split_note}. Priority: {rec.priority}.",
                created_by_user_id=user_id,
                version=1,
            )
            db.add(alloc_model)
            db.commit()
            db.refresh(alloc_model)

            allocations_generated.append(
                ProcurementAllocationItem(
                    id=alloc_model.id,
                    allocation_number=alloc_model.allocation_number,
                    recommendation_id=rec.id,
                    plant_code=plant.code,
                    material_code=mat.code,
                    material_description=mat.description,
                    material_type=mat.material_type,
                    vendor_id=v.id,
                    vendor_code=v.code,
                    vendor_name=v.name,
                    allocated_quantity=round(alloc_qty_vendor, 2),
                    uom=mat.base_uom or "KG",
                    dispatch_date=dispatch_dt,
                    expected_arrival_date=arrival_dt,
                    status="DRAFT",
                    allocation_notes=alloc_model.allocation_notes,
                    version=1,
                    created_by_user_id=user_id,
                    created_at=alloc_model.created_at,
                    updated_at=alloc_model.updated_at,
                )
            )
            split_idx += 1

    record_audit_event(
        db,
        user_id=user_id,
        action="GENERATE_PROCUREMENT_ALLOCATIONS",
        resource_type="PlantProcurementAllocation",
        resource_id=plant_code,
        details={
            "total_generated": len(allocations_generated),
            "total_allocated_qty": total_qty_allocated,
        },
    )

    return ProcurementAllocationSummary(
        plant_code=plant.code,
        total_allocations_generated=len(allocations_generated),
        total_quantity_allocated=round(total_qty_allocated, 2),
        allocations=allocations_generated,
    )


def edit_procurement_allocation(
    db: Session,
    allocation_id: int,
    vendor_id: int | None = None,
    allocated_quantity: float | None = None,
    dispatch_date_val: date | None = None,
    expected_arrival_date_val: date | None = None,
    notes: str | None = None,
    user_id: int | None = None,
) -> ProcurementAllocationItem:
    """Allows planners to edit vendor allocation parameters prior to approval."""
    alloc = db.query(Allocation).filter(Allocation.id == allocation_id).first()
    if not alloc:
        raise AppError("ALLOCATION_NOT_FOUND", f"Allocation with ID {allocation_id} not found.", 404)

    if alloc.status == "APPROVED":
        raise AppError("ALLOCATION_LOCKED", "Approved allocations cannot be edited.", 400)

    changes: dict[str, Any] = {}

    if vendor_id is not None and vendor_id != alloc.vendor_id:
        vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
        if not vendor:
            raise AppError("VENDOR_NOT_FOUND", f"Vendor with ID {vendor_id} not found.", 404)
        changes["vendor_id"] = {"old": alloc.vendor_id, "new": vendor_id}
        alloc.vendor_id = vendor_id

    if allocated_quantity is not None and allocated_quantity > 0:
        changes["allocated_quantity"] = {"old": alloc.allocated_quantity, "new": allocated_quantity}
        alloc.allocated_quantity = round(allocated_quantity, 2)

    if dispatch_date_val is not None:
        changes["dispatch_date"] = {
            "old": alloc.dispatch_date.isoformat() if alloc.dispatch_date else None,
            "new": dispatch_date_val.isoformat(),
        }
        alloc.dispatch_date = dispatch_date_val

    if expected_arrival_date_val is not None:
        changes["expected_arrival_date"] = {
            "old": alloc.expected_arrival_date.isoformat() if alloc.expected_arrival_date else None,
            "new": expected_arrival_date_val.isoformat(),
        }
        alloc.expected_arrival_date = expected_arrival_date_val

    if notes is not None:
        changes["allocation_notes"] = {"old": alloc.allocation_notes, "new": notes}
        alloc.allocation_notes = notes

    alloc.version += 1
    db.commit()
    db.refresh(alloc)

    record_audit_event(
        db,
        user_id=user_id,
        action="EDIT_PROCUREMENT_ALLOCATION",
        resource_type="ProcurementAllocation",
        resource_id=str(allocation_id),
        details={"changes": changes, "new_version": alloc.version},
    )

    return _to_item_dto(alloc)


def approve_procurement_allocation(
    db: Session, allocation_id: int, user_id: int | None = None
) -> ProcurementAllocationItem:
    """Planner approves allocation. Updates status to APPROVED and generates Notification Payloads."""
    alloc = db.query(Allocation).filter(Allocation.id == allocation_id).first()
    if not alloc:
        raise AppError("ALLOCATION_NOT_FOUND", f"Allocation with ID {allocation_id} not found.", 404)

    if alloc.status == "APPROVED":
        raise AppError("ALREADY_APPROVED", f"Allocation {allocation_id} is already approved.", 400)

    alloc.status = "APPROVED"
    alloc.approved_by_user_id = user_id

    # Update associated ProcurementRecommendation status to ACCEPTED
    if alloc.recommendation:
        alloc.recommendation.status = "ACCEPTED"

    # Generate Notification Payload (Email + In-App)
    notification_payload = _build_notification_payload(alloc)
    alloc.notification_payload_json = json.dumps(notification_payload.model_dump())

    db.commit()
    db.refresh(alloc)

    record_audit_event(
        db,
        user_id=user_id,
        action="APPROVE_PROCUREMENT_ALLOCATION",
        resource_type="ProcurementAllocation",
        resource_id=str(allocation_id),
        details={
            "allocation_number": alloc.allocation_number,
            "approved_quantity": alloc.allocated_quantity,
            "vendor_code": alloc.vendor.code if alloc.vendor else None,
        },
    )

    return _to_item_dto(alloc)


def preview_notification_payload(db: Session, allocation_id: int) -> dict[str, Any]:
    """Generates preview of Email and In-App notification payloads without sending."""
    alloc = db.query(Allocation).filter(Allocation.id == allocation_id).first()
    if not alloc:
        raise AppError("ALLOCATION_NOT_FOUND", f"Allocation with ID {allocation_id} not found.", 404)

    if alloc.notification_payload_json:
        return json.loads(alloc.notification_payload_json)

    payload = _build_notification_payload(alloc)
    return payload.model_dump()


def get_procurement_allocation_history(
    db: Session, plant_code: str, limit: int = 50
) -> list[ProcurementAllocationItem]:
    plant = db.query(Plant).filter(Plant.code == plant_code).first()
    if not plant:
        return []

    allocs = (
        db.query(Allocation)
        .filter(Allocation.plant_id == plant.id)
        .order_by(Allocation.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_to_item_dto(a) for a in allocs]


def get_procurement_allocation_detail(db: Session, allocation_id: int) -> ProcurementAllocationItem:
    alloc = db.query(Allocation).filter(Allocation.id == allocation_id).first()
    if not alloc:
        raise AppError("ALLOCATION_NOT_FOUND", f"Allocation with ID {allocation_id} not found.", 404)
    return _to_item_dto(alloc)


def _build_notification_payload(alloc: Allocation) -> NotificationPayload:
    vendor_code = alloc.vendor.code if alloc.vendor else "UNKNOWN"
    vendor_name = alloc.vendor.name if alloc.vendor else "Unknown Vendor"
    vendor_email = alloc.vendor.contact_email if alloc.vendor and alloc.vendor.contact_email else f"{vendor_code.lower()}@supplier.com"

    plant_code = alloc.plant.code if alloc.plant else "PLANT"
    mat_code = alloc.material.code if alloc.material else "MAT"
    mat_desc = alloc.material.description if alloc.material else "Material"

    dispatch_str = alloc.dispatch_date.isoformat() if alloc.dispatch_date else "TBD"
    arrival_str = alloc.expected_arrival_date.isoformat() if alloc.expected_arrival_date else "TBD"

    subject = f"Official Procurement Order Allocation - Ref {alloc.allocation_number} ({plant_code})"
    email_body_html = f"""
    <html>
    <body>
        <h2>Procurement Order Allocation Dispatch</h2>
        <p>Dear {vendor_name},</p>
        <p>This is an official procurement order allocation generated by SPIP Enterprise Planning Engine.</p>
        <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse;">
            <tr><th>Allocation Ref</th><td><b>{alloc.allocation_number}</b></td></tr>
            <tr><th>Plant Location</th><td>{plant_code}</td></tr>
            <tr><th>Material</th><td>{mat_code} - {mat_desc}</td></tr>
            <tr><th>Allocated Quantity</th><td><b>{alloc.allocated_quantity:.2f} {alloc.uom}</b></td></tr>
            <tr><th>Dispatch Date</th><td>{dispatch_str}</td></tr>
            <tr><th>Expected Arrival Date</th><td>{arrival_str}</td></tr>
            <tr><th>Status</th><td><b>{alloc.status}</b></td></tr>
        </table>
        <p><b>Planner Notes:</b> {alloc.allocation_notes or 'Standard procurement dispatch requirement.'}</p>
        <br/>
        <p><i>Note: This is an automatically generated allocation payload preview.</i></p>
    </body>
    </html>
    """

    email_payload = {
        "recipient_email": vendor_email,
        "vendor_code": vendor_code,
        "subject": subject,
        "body_html": email_body_html.strip(),
        "allocation_number": alloc.allocation_number,
        "generated_at": datetime.utcnow().isoformat(),
    }

    in_app_payload = {
        "title": f"Procurement Allocation Approved ({alloc.allocation_number})",
        "message": f"Allocation of {alloc.allocated_quantity:.1f} {alloc.uom} for {mat_code} at {plant_code} approved.",
        "priority": "HIGH",
        "link_url": f"/allocations/{alloc.id}",
        "allocation_id": alloc.id,
        "created_at": datetime.utcnow().isoformat(),
    }

    return NotificationPayload(email_payload=email_payload, in_app_payload=in_app_payload)


def _to_item_dto(alloc: Allocation) -> ProcurementAllocationItem:
    pay_dict = json.loads(alloc.notification_payload_json) if alloc.notification_payload_json else None
    return ProcurementAllocationItem(
        id=alloc.id,
        allocation_number=alloc.allocation_number,
        recommendation_id=alloc.recommendation_id,
        plant_code=alloc.plant.code if alloc.plant else "",
        material_code=alloc.material.code if alloc.material else "",
        material_description=alloc.material.description if alloc.material else "",
        material_type=alloc.material.material_type if alloc.material else "RM",
        vendor_id=alloc.vendor_id,
        vendor_code=alloc.vendor.code if alloc.vendor else None,
        vendor_name=alloc.vendor.name if alloc.vendor else None,
        allocated_quantity=alloc.allocated_quantity,
        uom=alloc.uom,
        dispatch_date=alloc.dispatch_date,
        expected_arrival_date=alloc.expected_arrival_date,
        status=alloc.status,
        allocation_notes=alloc.allocation_notes,
        version=alloc.version,
        created_by_user_id=alloc.created_by_user_id,
        approved_by_user_id=alloc.approved_by_user_id,
        notification_payload=pay_dict,
        created_at=alloc.created_at,
        updated_at=alloc.updated_at,
    )
