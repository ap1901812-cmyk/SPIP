from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.db.models.user import RoleEnum, User
from app.services.planning.allocation_engine import (
    ProcurementAllocationItem,
    ProcurementAllocationSummary,
    approve_procurement_allocation,
    edit_procurement_allocation,
    generate_procurement_allocations,
    get_procurement_allocation_detail,
    get_procurement_allocation_history,
    preview_notification_payload,
)

router = APIRouter(prefix="/planning/procurement-allocations", tags=["procurement-allocations"])


class GenerateAllocationsRequest(BaseModel):
    plant_code: str = Field(..., description="Plant code to generate allocations for")
    recommendation_ids: list[int] | None = Field(None, description="Optional filter of recommendation IDs")


class EditAllocationRequest(BaseModel):
    vendor_id: int | None = Field(None, description="Updated vendor ID")
    allocated_quantity: float | None = Field(None, gt=0, description="Updated allocated quantity")
    dispatch_date: date | None = Field(None, description="Updated dispatch date")
    expected_arrival_date: date | None = Field(None, description="Updated expected arrival date")
    allocation_notes: str | None = Field(None, description="Updated allocation notes")


@router.post(
    "/generate",
    response_model=ProcurementAllocationSummary,
    summary="Generate Vendor Allocations",
    description="Converts Phase 9 Procurement Recommendations into dynamic vendor allocations (DRAFT status).",
)
def api_generate_procurement_allocations(
    req: GenerateAllocationsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleEnum.ADMIN.value, RoleEnum.PLANNER.value, RoleEnum.MANAGER_APPROVER.value)
    ),
) -> ProcurementAllocationSummary:
    return generate_procurement_allocations(
        db=db,
        plant_code=req.plant_code,
        recommendation_ids=req.recommendation_ids,
        user_id=current_user.id,
    )


@router.put(
    "/{allocation_id}",
    response_model=ProcurementAllocationItem,
    summary="Edit Vendor Allocation",
    description="Allows planners to edit vendor, quantity, dates, or notes for a draft allocation prior to approval.",
)
def api_edit_procurement_allocation(
    allocation_id: int,
    req: EditAllocationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleEnum.ADMIN.value, RoleEnum.PLANNER.value, RoleEnum.MANAGER_APPROVER.value)
    ),
) -> ProcurementAllocationItem:
    return edit_procurement_allocation(
        db=db,
        allocation_id=allocation_id,
        vendor_id=req.vendor_id,
        allocated_quantity=req.allocated_quantity,
        dispatch_date_val=req.dispatch_date,
        expected_arrival_date_val=req.expected_arrival_date,
        notes=req.allocation_notes,
        user_id=current_user.id,
    )


@router.post(
    "/{allocation_id}/approve",
    response_model=ProcurementAllocationItem,
    summary="Approve Vendor Allocation",
    description="Planner approves allocation, updates status to APPROVED, and generates notification payloads.",
)
def api_approve_procurement_allocation(
    allocation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleEnum.ADMIN.value, RoleEnum.PLANNER.value, RoleEnum.MANAGER_APPROVER.value)
    ),
) -> ProcurementAllocationItem:
    return approve_procurement_allocation(db=db, allocation_id=allocation_id, user_id=current_user.id)


@router.get(
    "",
    summary="List Allocation History",
    description="Retrieves procurement allocation history for a plant.",
)
def api_list_procurement_allocations(
    plant_code: str = Query(..., description="Plant code filter"),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProcurementAllocationItem]:
    return get_procurement_allocation_history(db=db, plant_code=plant_code, limit=limit)


@router.get(
    "/{allocation_id}",
    response_model=ProcurementAllocationItem,
    summary="Get Allocation Details",
    description="Retrieves full details for a specific procurement allocation.",
)
def api_get_procurement_allocation_detail(
    allocation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProcurementAllocationItem:
    return get_procurement_allocation_detail(db=db, allocation_id=allocation_id)


@router.get(
    "/{allocation_id}/notifications",
    summary="Preview Notification Payload",
    description="Generates preview of Email and In-App notification payloads without sending.",
)
def api_preview_notification_payload(
    allocation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return preview_notification_payload(db=db, allocation_id=allocation_id)
