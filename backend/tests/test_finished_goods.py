from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.db.models.user import RoleEnum, User, UserRole
from app.services.sap import MockSAPAdapter


def _seed_user(db: Session, email: str, role_name: str) -> str:
    user = User(
        email=email,
        full_name=f"{role_name} User",
        hashed_password=hash_password("Pass123!"),
        is_active=True,
    )
    user.roles.append(UserRole(role_name=role_name))
    db.add(user)
    db.commit()
    db.refresh(user)
    return create_access_token(user_id=user.id, email=user.email, roles=[role_name])


def test_list_finished_goods(client: TestClient, db_session: Session) -> None:
    token = _seed_user(db_session, "fg_user1@spip.local", RoleEnum.READ_ONLY.value)
    MockSAPAdapter().sync_to_database(db_session)

    res = client.get("/api/v1/finished-goods", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    fg_list = res.json()
    assert len(fg_list) >= 2
    assert all(fg["material_type"] == "FG" for fg in fg_list)


def test_get_finished_good_detail(client: TestClient, db_session: Session) -> None:
    token = _seed_user(db_session, "fg_user2@spip.local", RoleEnum.READ_ONLY.value)
    MockSAPAdapter().sync_to_database(db_session)

    # Fetch FG list first to get a valid FG ID
    res_list = client.get("/api/v1/finished-goods", headers={"Authorization": f"Bearer {token}"})
    assert res_list.status_code == 200
    fg_id = res_list.json()[0]["id"]

    res_detail = client.get(f"/api/v1/finished-goods/{fg_id}", headers={"Authorization": f"Bearer {token}"})
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["id"] == fg_id
    assert detail["material_type"] == "FG"
    assert "rm_components_count" in detail
    assert "pm_components_count" in detail


def test_get_finished_good_bom_expansion(client: TestClient, db_session: Session) -> None:
    token = _seed_user(db_session, "fg_user3@spip.local", RoleEnum.READ_ONLY.value)
    MockSAPAdapter().sync_to_database(db_session)

    res_list = client.get("/api/v1/finished-goods", headers={"Authorization": f"Bearer {token}"})
    fg_id = res_list.json()[0]["id"]

    res_exp = client.get(f"/api/v1/finished-goods/{fg_id}/bom", headers={"Authorization": f"Bearer {token}"})
    assert res_exp.status_code == 200
    exp = res_exp.json()
    assert exp["fg_material_id"] == fg_id
    assert "rm_components" in exp
    assert "pm_components" in exp


def test_finished_goods_not_found(client: TestClient, db_session: Session) -> None:
    token = _seed_user(db_session, "fg_user4@spip.local", RoleEnum.READ_ONLY.value)
    res = client.get("/api/v1/finished-goods/99999", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404
