from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import create_access_token, hash_password
from app.db.models.domain import (
    Allocation,
    AllocationStatusEnum,
    InventorySnapshot,
    Material,
    Plant,
)
from app.db.models.user import RoleEnum, User, UserRole
from app.services.allocation import approve_allocation, reject_allocation, submit_allocation
from app.services.notification.email import MockEmailAdapter, SMTPEmailAdapter, get_email_adapter
from app.services.notification.service import (
    create_notification,
    get_unread_count,
    get_user_notifications,
    mark_all_notifications_as_read,
    mark_notification_as_read,
)


def _seed_test_user(db: Session, email: str, role_name: str) -> User:
    user = User(
        email=email,
        full_name=f"User {email}",
        hashed_password=hash_password("Pass123!"),
        is_active=True,
    )
    db.add(user)
    db.flush()
    role = UserRole(user_id=user.id, role_name=role_name)
    db.add(role)
    db.commit()
    db.refresh(user)
    return user


def _auth_header(user: User) -> dict[str, str]:
    roles = [r.role_name for r in user.roles]
    token = create_access_token(user_id=user.id, email=user.email, roles=roles)
    return {"Authorization": f"Bearer {token}"}


def test_email_adapter_mock_and_smtp_modes():
    adapter = get_email_adapter()
    assert isinstance(adapter, MockEmailAdapter)
    if isinstance(adapter, MockEmailAdapter):
        adapter.clear()
        assert len(adapter.sent_emails) == 0
        res = adapter.send_email("test@spip.local", "Subject", "Body")
        assert res is True
        assert len(adapter.sent_emails) == 1
        assert adapter.sent_emails[0]["to_email"] == "test@spip.local"

    smtp_settings = Settings(
        database_url="postgresql+psycopg://spip_user:spip_dev_password@db:5432/spip_db",
        email_adapter_mode="smtp",
        smtp_enabled=True,
        smtp_host="invalid-host-for-testing",
        smtp_port=1025,
    )
    smtp_adapter = get_email_adapter(smtp_settings)
    assert isinstance(smtp_adapter, SMTPEmailAdapter)
    assert smtp_adapter.send_email("user@spip.local", "Test", "Body") is False


def test_notification_service_lifecycle(db_session: Session):
    u1 = _seed_test_user(db_session, "notif1@spip.local", RoleEnum.PLANNER.value)
    u2 = _seed_test_user(db_session, "notif2@spip.local", RoleEnum.READ_ONLY.value)

    n1 = create_notification(
        db_session,
        recipient_user_id=u1.id,
        notification_type="TEST_TYPE",
        title="Test Title 1",
        message="Test Message 1",
    )
    create_notification(
        db_session,
        recipient_user_id=u1.id,
        notification_type="TEST_TYPE",
        title="Test Title 2",
        message="Test Message 2",
    )
    db_session.commit()

    assert get_unread_count(db_session, u1.id) == 2
    assert get_unread_count(db_session, u2.id) == 0

    items, total = get_user_notifications(db_session, u1.id)
    assert total == 2
    assert len(items) == 2

    # Mark single as read
    updated = mark_notification_as_read(db_session, u1.id, n1.id)
    assert updated.is_read is True
    assert get_unread_count(db_session, u1.id) == 1

    # Mark all as read
    count = mark_all_notifications_as_read(db_session, u1.id)
    assert count == 1
    assert get_unread_count(db_session, u1.id) == 0


def test_business_events_trigger_notifications(db_session: Session):
    planner = _seed_test_user(db_session, "planner_event@spip.local", RoleEnum.PLANNER.value)
    manager = _seed_test_user(db_session, "mgr_event@spip.local", RoleEnum.MANAGER_APPROVER.value)

    plant = Plant(code="PLANT-EV", name="Event Plant")
    material = Material(code="MAT-EV", description="Event Mat", base_uom="KG")
    db_session.add_all([plant, material])
    db_session.commit()

    inv = InventorySnapshot(
        plant_id=plant.id,
        material_id=material.id,
        snapshot_date=date.today(),
        usable_physical_stock=500.0,
        uom="KG",
    )
    db_session.add(inv)
    db_session.commit()

    alloc = Allocation(
        allocation_number="ALC-EV-001",
        plant_id=plant.id,
        material_id=material.id,
        allocated_quantity=50.0,
        uom="KG",
        status=AllocationStatusEnum.DRAFT.value,
        created_by_user_id=planner.id,
    )
    db_session.add(alloc)
    db_session.commit()

    # 1. Submit Allocation -> Notifies Manager
    submit_allocation(db_session, alloc.id, planner)
    assert get_unread_count(db_session, manager.id) == 1
    mgr_notifs, _ = get_user_notifications(db_session, manager.id)
    assert mgr_notifs[0].notification_type == "ALLOCATION_PENDING_APPROVAL"

    # 2. Approve Allocation -> Notifies Planner
    approve_allocation(db_session, alloc.id, manager)
    assert get_unread_count(db_session, planner.id) == 1
    planner_notifs, _ = get_user_notifications(db_session, planner.id)
    assert planner_notifs[0].notification_type == "ALLOCATION_APPROVED"

    # 3. Reject Allocation event test
    alloc2 = Allocation(
        allocation_number="ALC-EV-002",
        plant_id=plant.id,
        material_id=material.id,
        allocated_quantity=30.0,
        uom="KG",
        status=AllocationStatusEnum.PENDING_APPROVAL.value,
        created_by_user_id=planner.id,
    )
    db_session.add(alloc2)
    db_session.commit()

    reject_allocation(db_session, alloc2.id, "Over capacity", manager)
    planner_notifs2, _ = get_user_notifications(db_session, planner.id)
    assert planner_notifs2[0].notification_type == "ALLOCATION_REJECTED"
    assert "Over capacity" in planner_notifs2[0].message


def test_notifications_api_endpoints_and_isolation(client, db_session: Session):
    u1 = _seed_test_user(db_session, "api_u1@spip.local", RoleEnum.PLANNER.value)
    u2 = _seed_test_user(db_session, "api_u2@spip.local", RoleEnum.READ_ONLY.value)

    h1 = _auth_header(u1)
    h2 = _auth_header(u2)

    # 1. Unauthenticated rejection
    res = client.get("/api/v1/notifications")
    assert res.status_code == 401

    # 2. Create notification for u1
    n = create_notification(
        db_session,
        recipient_user_id=u1.id,
        notification_type="TEST_TYPE",
        title="Title U1",
        message="Message U1",
    )
    db_session.commit()

    # 3. User 1 can access notification
    res = client.get("/api/v1/notifications", headers=h1)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Title U1"

    # User 1 unread count
    res_uc = client.get("/api/v1/notifications/unread-count", headers=h1)
    assert res_uc.status_code == 200
    assert res_uc.json()["unread_count"] == 1

    # 4. User 2 gets empty notification list (isolation)
    res_u2 = client.get("/api/v1/notifications", headers=h2)
    assert res_u2.status_code == 200
    assert res_u2.json()["total"] == 0

    # User 2 cannot mark User 1's notification as read (403 forbidden)
    res_forbidden = client.patch(f"/api/v1/notifications/{n.id}/read", headers=h2)
    assert res_forbidden.status_code == 403

    # User 1 marks as read
    res_read = client.patch(f"/api/v1/notifications/{n.id}/read", headers=h1)
    assert res_read.status_code == 200
    assert res_read.json()["is_read"] is True

    # User 1 mark all read
    res_mar = client.post("/api/v1/notifications/mark-all-read", headers=h1)
    assert res_mar.status_code == 200
    assert res_mar.json()["unread_count"] == 0
