from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.db.models.domain import Material, MaterialTypeEnum
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


def test_material_classification_and_filtering(client: TestClient, db_session: Session) -> None:
    token = _seed_user(db_session, "viewer@spip.local", RoleEnum.READ_ONLY.value)
    MockSAPAdapter().sync_to_database(db_session)

    # Filter FG materials
    res_fg = client.get("/api/v1/materials?material_type=FG", headers={"Authorization": f"Bearer {token}"})
    assert res_fg.status_code == 200
    fg_mats = res_fg.json()
    assert len(fg_mats) >= 2
    assert all(m["material_type"] == "FG" for m in fg_mats)

    # Filter RM materials
    res_rm = client.get("/api/v1/materials?material_type=RM", headers={"Authorization": f"Bearer {token}"})
    assert res_rm.status_code == 200
    rm_mats = res_rm.json()
    assert len(rm_mats) >= 2
    assert all(m["material_type"] == "RM" for m in rm_mats)

    # Filter PM materials
    res_pm = client.get("/api/v1/materials?material_type=PM", headers={"Authorization": f"Bearer {token}"})
    assert res_pm.status_code == 200
    pm_mats = res_pm.json()
    assert len(pm_mats) >= 2
    assert all(m["material_type"] == "PM" for m in pm_mats)


def test_bom_api_crud_flow(client: TestClient, db_session: Session) -> None:
    planner_token = _seed_user(db_session, "planner_bom@spip.local", RoleEnum.PLANNER.value)
    admin_token = _seed_user(db_session, "admin_bom@spip.local", RoleEnum.ADMIN.value)
    read_token = _seed_user(db_session, "read_bom@spip.local", RoleEnum.READ_ONLY.value)

    # 1. Create FG and Component Materials
    fg = Material(code="FG-TEST-01", description="Test FG Material", material_type=MaterialTypeEnum.FG.value, base_uom="PCS")
    rm = Material(code="RM-TEST-01", description="Test RM Component", material_type=MaterialTypeEnum.RM.value, base_uom="KG")
    db_session.add_all([fg, rm])
    db_session.commit()
    db_session.refresh(fg)
    db_session.refresh(rm)

    # 2. List BOMs (initially empty)
    res_list = client.get("/api/v1/boms", headers={"Authorization": f"Bearer {read_token}"})
    assert res_list.status_code == 200
    assert len(res_list.json()) == 0

    # 3. Create BOM entry as Read-Only (should fail 403)
    res_create_forbidden = client.post(
        "/api/v1/boms",
        json={"fg_material_id": fg.id, "component_material_id": rm.id, "required_quantity": 4.5, "unit_of_measure": "KG"},
        headers={"Authorization": f"Bearer {read_token}"},
    )
    assert res_create_forbidden.status_code == 403

    # 4. Create BOM entry as Planner (should succeed 201)
    res_create = client.post(
        "/api/v1/boms",
        json={"fg_material_id": fg.id, "component_material_id": rm.id, "required_quantity": 4.5, "unit_of_measure": "KG"},
        headers={"Authorization": f"Bearer {planner_token}"},
    )
    assert res_create.status_code == 201
    bom_data = res_create.json()
    bom_id = bom_data["id"]
    assert bom_data["fg_material_id"] == fg.id
    assert bom_data["component_material_id"] == rm.id
    assert bom_data["required_quantity"] == 4.5
    assert bom_data["unit_of_measure"] == "KG"

    # 5. Get single BOM by ID
    res_get = client.get(f"/api/v1/boms/{bom_id}", headers={"Authorization": f"Bearer {read_token}"})
    assert res_get.status_code == 200
    assert res_get.json()["id"] == bom_id
    assert res_get.json()["fg_material"]["code"] == "FG-TEST-01"

    # 6. Update BOM entry as Planner
    res_update = client.put(
        f"/api/v1/boms/{bom_id}",
        json={"required_quantity": 5.0, "is_active": False},
        headers={"Authorization": f"Bearer {planner_token}"},
    )
    assert res_update.status_code == 200
    assert res_update.json()["required_quantity"] == 5.0
    assert res_update.json()["is_active"] is False

    # 7. Delete BOM as Admin
    res_delete = client.delete(f"/api/v1/boms/{bom_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_delete.status_code == 204

    # Verify deleted
    res_get_deleted = client.get(f"/api/v1/boms/{bom_id}", headers={"Authorization": f"Bearer {read_token}"})
    assert res_get_deleted.status_code == 404


def test_bom_validation_rules(client: TestClient, db_session: Session) -> None:
    planner_token = _seed_user(db_session, "planner_val@spip.local", RoleEnum.PLANNER.value)

    mat1 = Material(code="MAT-VAL-01", description="Val Mat 1", material_type="FG", base_uom="PCS")
    mat2 = Material(code="MAT-VAL-02", description="Val Mat 2", material_type="RM", base_uom="KG")
    db_session.add_all([mat1, mat2])
    db_session.commit()
    db_session.refresh(mat1)
    db_session.refresh(mat2)

    # Self reference check
    res_self = client.post(
        "/api/v1/boms",
        json={"fg_material_id": mat1.id, "component_material_id": mat1.id, "required_quantity": 1.0},
        headers={"Authorization": f"Bearer {planner_token}"},
    )
    assert res_self.status_code == 400

    # Non-existent material
    res_nonexistent = client.post(
        "/api/v1/boms",
        json={"fg_material_id": mat1.id, "component_material_id": 99999, "required_quantity": 1.0},
        headers={"Authorization": f"Bearer {planner_token}"},
    )
    assert res_nonexistent.status_code == 404

    # Successful creation
    res_ok = client.post(
        "/api/v1/boms",
        json={"fg_material_id": mat1.id, "component_material_id": mat2.id, "required_quantity": 1.0},
        headers={"Authorization": f"Bearer {planner_token}"},
    )
    assert res_ok.status_code == 201

    # Duplicate creation attempt
    res_dup = client.post(
        "/api/v1/boms",
        json={"fg_material_id": mat1.id, "component_material_id": mat2.id, "required_quantity": 2.0},
        headers={"Authorization": f"Bearer {planner_token}"},
    )
    assert res_dup.status_code == 409
