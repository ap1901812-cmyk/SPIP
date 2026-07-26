from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.db.models.domain import Allocation
from app.db.models.user import RoleEnum, User
from app.schemas.allocation import (
    AllocationCreateSchema,
    AllocationRejectSchema,
    AllocationResponseSchema,
    AllocationUpdateSchema,
)
from app.services.allocation import (
    AllocationError,
    approve_allocation,
    create_allocation,
    reject_allocation,
    submit_allocation,
    update_allocation,
)

router = APIRouter(prefix="/allocations", tags=["allocations"])

planner_or_admin_role = require_roles(RoleEnum.PLANNER, RoleEnum.ADMIN)
manager_or_admin_role = require_roles(RoleEnum.MANAGER_APPROVER, RoleEnum.ADMIN)



def _to_response_schema(alloc: Allocation) -> AllocationResponseSchema:
    return AllocationResponseSchema(
        id=alloc.id,
        allocation_number=alloc.allocation_number,
        plant_code=alloc.plant.code if alloc.plant else "",
        plant_name=alloc.plant.name if alloc.plant else "",
        material_code=alloc.material.code if alloc.material else "",
        material_description=alloc.material.description if alloc.material else "",
        vendor_code=alloc.vendor.code if alloc.vendor else None,
        vendor_name=alloc.vendor.name if alloc.vendor else None,
        allocated_quantity=alloc.allocated_quantity,
        uom=alloc.uom,
        status=alloc.status,
        created_by_email=alloc.created_by_user.email if alloc.created_by_user else "",
        approved_by_email=alloc.approved_by_user.email if alloc.approved_by_user else None,
        rejection_reason=alloc.rejection_reason,
        sap_reference_id=alloc.sap_reference_id,
        version=alloc.version,
        created_at=alloc.created_at,
        updated_at=alloc.updated_at,
    )


@router.post("", response_model=AllocationResponseSchema)
def api_create_allocation(
    schema: AllocationCreateSchema,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(planner_or_admin_role)],
) -> AllocationResponseSchema:
    alloc = create_allocation(db=db, schema=schema, creator_user=current_user)
    return _to_response_schema(alloc)


@router.get("", response_model=list[AllocationResponseSchema])
def api_list_allocations(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    plant_code: Annotated[str | None, Query()] = None,
    material_code: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
) -> list[AllocationResponseSchema]:
    query = db.query(Allocation)
    if plant_code:
        query = query.filter(Allocation.plant.has(code=plant_code))
    if material_code:
        query = query.filter(Allocation.material.has(code=material_code))
    if status:
        query = query.filter(Allocation.status == status)

    allocs = query.order_by(Allocation.id.desc()).all()
    return [_to_response_schema(a) for a in allocs]


@router.get("/{allocation_id}", response_model=AllocationResponseSchema)
def api_get_allocation(
    allocation_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AllocationResponseSchema:
    alloc = db.query(Allocation).filter(Allocation.id == allocation_id).first()
    if not alloc:
        raise AllocationError(f"Allocation with ID {allocation_id} not found.", 404)
    return _to_response_schema(alloc)


@router.put("/{allocation_id}", response_model=AllocationResponseSchema)
def api_update_allocation(
    allocation_id: int,
    schema: AllocationUpdateSchema,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(planner_or_admin_role)],
) -> AllocationResponseSchema:
    alloc = update_allocation(
        db=db, allocation_id=allocation_id, schema=schema, user=current_user
    )
    return _to_response_schema(alloc)


@router.post("/{allocation_id}/submit", response_model=AllocationResponseSchema)
def api_submit_allocation(
    allocation_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(planner_or_admin_role)],
) -> AllocationResponseSchema:
    alloc = submit_allocation(db=db, allocation_id=allocation_id, user=current_user)
    return _to_response_schema(alloc)


@router.post("/{allocation_id}/approve", response_model=AllocationResponseSchema)
def api_approve_allocation(
    allocation_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(manager_or_admin_role)],
) -> AllocationResponseSchema:
    alloc = approve_allocation(db=db, allocation_id=allocation_id, approver_user=current_user)
    return _to_response_schema(alloc)


@router.post("/{allocation_id}/reject", response_model=AllocationResponseSchema)
def api_reject_allocation(
    allocation_id: int,
    schema: AllocationRejectSchema,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(manager_or_admin_role)],
) -> AllocationResponseSchema:
    alloc = reject_allocation(
        db=db,
        allocation_id=allocation_id,
        rejection_reason=schema.rejection_reason,
        approver_user=current_user,
    )
    return _to_response_schema(alloc)
