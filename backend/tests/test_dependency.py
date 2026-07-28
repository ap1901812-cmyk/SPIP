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


def test_material_where_used(client: TestClient, db_session: Session) -> None:
    token = _seed_user(db_session, "dep_user1@spip.local", RoleEnum.READ_ONLY.value)
    MockSAPAdapter().sync_to_database(db_session)

    # Fetch materials to find an RM component
    res_mats = client.get("/api/v1/materials?material_type=RM", headers={"Authorization": f"Bearer {token}"})
    assert res_mats.status_code == 200
    rm_id = res_mats.json()[0]["id"]

    res_wu = client.get(f"/api/v1/materials/{rm_id}/where-used", headers={"Authorization": f"Bearer {token}"})
    assert res_wu.status_code == 200
    wu_data = res_wu.json()
    assert wu_data["component_material_id"] == rm_id
    assert "where_used" in wu_data
    assert "total_where_used" in wu_data


def test_material_dependencies(client: TestClient, db_session: Session) -> None:
    token = _seed_user(db_session, "dep_user2@spip.local", RoleEnum.READ_ONLY.value)
    MockSAPAdapter().sync_to_database(db_session)

    res_mats = client.get("/api/v1/materials", headers={"Authorization": f"Bearer {token}"})
    mat_id = res_mats.json()[0]["id"]

    res_dep = client.get(f"/api/v1/materials/{mat_id}/dependencies", headers={"Authorization": f"Bearer {token}"})
    assert res_dep.status_code == 200
    dep_data = res_dep.json()
    assert dep_data["material_id"] == mat_id
    assert "upstream_finished_goods" in dep_data
    assert "downstream_components" in dep_data


def test_dependency_not_found(client: TestClient, db_session: Session) -> None:
    token = _seed_user(db_session, "dep_user3@spip.local", RoleEnum.READ_ONLY.value)
    res_wu = client.get("/api/v1/materials/99999/where-used", headers={"Authorization": f"Bearer {token}"})
    assert res_wu.status_code == 404

    res_dep = client.get("/api/v1/materials/99999/dependencies", headers={"Authorization": f"Bearer {token}"})
    assert res_dep.status_code == 404
