from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.db.models.domain import (
    AllocationStatusEnum,
    InventorySnapshot,
    Material,
    Plant,
)
from app.db.models.user import RoleEnum, User, UserRole
from app.schemas.allocation import AllocationCreateSchema, AllocationUpdateSchema
from app.services.allocation import (
    AllocationConcurrencyError,
    AllocationError,
    approve_allocation,
    create_allocation,
    reject_allocation,
    submit_allocation,
    update_allocation,
)
from app.services.planning import calculate_planning_availability


def _seed_test_user(db: Session, email: str, role_name: str) -> User:
    user = User(email=email, full_name=f"Test {role_name}", hashed_password="pwd", is_active=True)
    user.roles.append(UserRole(role_name=role_name))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _seed_allocation_domain_data(db: Session) -> tuple[Plant, Material, User, User]:
    plant = Plant(code="PLANT-ALC", name="Allocation Test Plant")
    material = Material(code="MAT-ALC", description="Allocation Test Material", base_uom="KG")
    db.add_all([plant, material])
    db.commit()

    db.add(
        InventorySnapshot(
            plant_id=plant.id,
            material_id=material.id,
            snapshot_date=date.today(),
            usable_physical_stock=1000.0,
            uom="KG",
        )
    )
    db.commit()

    planner = _seed_test_user(db, "planner_alc@spip.local", RoleEnum.PLANNER.value)
    manager = _seed_test_user(db, "mgr_alc@spip.local", RoleEnum.MANAGER_APPROVER.value)
    return plant, material, planner, manager



def test_allocation_create_success_and_over_allocation_rejection(db_session: Session) -> None:
    plant, material, planner, _ = _seed_allocation_domain_data(db_session)

    schema = AllocationCreateSchema(
        plant_code=plant.code,
        material_code=material.code,
        allocated_quantity=500.0,
        uom="KG",
    )
    alloc = create_allocation(db_session, schema, planner)
    assert alloc.id is not None
    assert alloc.status == AllocationStatusEnum.DRAFT.value
    assert alloc.allocated_quantity == 500.0

    over_schema = AllocationCreateSchema(
        plant_code=plant.code,
        material_code=material.code,
        allocated_quantity=1500.0,
        uom="KG",
    )
    with pytest.raises(AllocationError) as exc_info:
        create_allocation(db_session, over_schema, planner)
    assert "exceeds effective Planning Availability" in str(exc_info.value)


def test_current_edit_exclusion_rule(db_session: Session) -> None:
    plant, material, planner, _ = _seed_allocation_domain_data(db_session)

    schema = AllocationCreateSchema(
        plant_code=plant.code,
        material_code=material.code,
        allocated_quantity=600.0,
        uom="KG",
    )
    alloc = create_allocation(db_session, schema, planner)
    alloc = submit_allocation(db_session, alloc.id, planner)
    assert alloc.status == AllocationStatusEnum.PENDING_APPROVAL.value

    avail = calculate_planning_availability(db_session, plant.id, material.id)
    assert avail.committed_allocations == 600.0
    assert avail.planning_availability == 400.0

    # CURRENT-EDIT EXCLUSION PROOF:
    # Updating allocation X from 600 KG to 800 KG succeeds because X itself is excluded
    update_schema = AllocationUpdateSchema(allocated_quantity=800.0, version=alloc.version)
    updated_alloc = update_allocation(db_session, alloc.id, update_schema, planner)

    assert updated_alloc.allocated_quantity == 800.0
    assert updated_alloc.version == 3

    over_update = AllocationUpdateSchema(allocated_quantity=1200.0, version=updated_alloc.version)
    with pytest.raises(AllocationError) as exc_info:
        update_allocation(db_session, alloc.id, over_update, planner)
    assert "exceeds available capacity" in str(exc_info.value)


def test_allocation_concurrency_protection(db_session: Session) -> None:
    plant, material, planner, _ = _seed_allocation_domain_data(db_session)
    schema = AllocationCreateSchema(
        plant_code=plant.code, material_code=material.code, allocated_quantity=300.0
    )
    alloc = create_allocation(db_session, schema, planner)

    stale_update = AllocationUpdateSchema(allocated_quantity=400.0, version=999)
    with pytest.raises(AllocationConcurrencyError) as exc_info:
        update_allocation(db_session, alloc.id, stale_update, planner)
    assert exc_info.value.status_code == 409


def test_manager_approval_workflow_and_sap_writeback(db_session: Session) -> None:
    plant, material, planner, manager = _seed_allocation_domain_data(db_session)
    schema = AllocationCreateSchema(
        plant_code=plant.code, material_code=material.code, allocated_quantity=250.0
    )
    alloc = create_allocation(db_session, schema, planner)
    alloc = submit_allocation(db_session, alloc.id, planner)

    approved_alloc = approve_allocation(db_session, alloc.id, manager)

    assert approved_alloc.status == AllocationStatusEnum.APPROVED.value
    assert approved_alloc.approved_by_user_id == manager.id
    assert approved_alloc.sap_reference_id is not None
    assert approved_alloc.sap_reference_id.startswith("SAP-PO-")

    with pytest.raises(AllocationError) as exc_info:
        approve_allocation(db_session, alloc.id, manager)
    assert "Cannot approve allocation in status 'APPROVED'" in str(exc_info.value)


def test_manager_rejection_workflow(db_session: Session) -> None:
    plant, material, planner, manager = _seed_allocation_domain_data(db_session)
    schema = AllocationCreateSchema(
        plant_code=plant.code, material_code=material.code, allocated_quantity=150.0
    )
    alloc = create_allocation(db_session, schema, planner)
    alloc = submit_allocation(db_session, alloc.id, planner)

    rejected_alloc = reject_allocation(
        db_session, alloc.id, "Vendor pricing not optimal", manager
    )

    assert rejected_alloc.status == AllocationStatusEnum.REJECTED.value
    assert rejected_alloc.rejection_reason == "Vendor pricing not optimal"

    avail = calculate_planning_availability(db_session, plant.id, material.id)
    assert avail.committed_allocations == 0.0
    assert avail.planning_availability == 1000.0
