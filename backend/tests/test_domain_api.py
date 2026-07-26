from __future__ import annotations

import io

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.db.models.user import RoleEnum, User, UserRole
from app.services.sap import MockSAPAdapter
from tests.test_ingestion import _create_mock_xlsx_bytes


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


def test_plants_api_auth_required(client: TestClient) -> None:
    res = client.get("/api/v1/plants")
    assert res.status_code == 401


def test_plants_api_authenticated(client: TestClient, db_session: Session) -> None:
    token = _seed_user(db_session, "read@spip.local", RoleEnum.READ_ONLY.value)
    MockSAPAdapter().sync_to_database(db_session)

    res = client.get("/api/v1/plants", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    plants = res.json()
    assert len(plants) >= 2


def test_materials_api_authenticated(client: TestClient, db_session: Session) -> None:
    token = _seed_user(db_session, "read2@spip.local", RoleEnum.READ_ONLY.value)
    MockSAPAdapter().sync_to_database(db_session)

    res = client.get("/api/v1/materials", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    materials = res.json()
    assert len(materials) >= 5


def test_inventory_and_consumption_apis(client: TestClient, db_session: Session) -> None:
    token = _seed_user(db_session, "planner@spip.local", RoleEnum.PLANNER.value)
    MockSAPAdapter().sync_to_database(db_session)

    res_inv = client.get(
        "/api/v1/inventory?plant_code=PLANT-1000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_inv.status_code == 200
    assert len(res_inv.json()) > 0

    res_cons = client.get(
        "/api/v1/consumption?plant_code=PLANT-1000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_cons.status_code == 200
    assert len(res_cons.json()) > 0


def test_sap_sync_api_rbac(client: TestClient, db_session: Session) -> None:
    read_token = _seed_user(db_session, "readonly@spip.local", RoleEnum.READ_ONLY.value)
    planner_token = _seed_user(db_session, "planner2@spip.local", RoleEnum.PLANNER.value)

    res_forbidden = client.post(
        "/api/v1/sap/sync", headers={"Authorization": f"Bearer {read_token}"}
    )
    assert res_forbidden.status_code == 403

    res_success = client.post(
        "/api/v1/sap/sync", headers={"Authorization": f"Bearer {planner_token}"}
    )
    assert res_success.status_code == 200
    assert res_success.json()["status"] == "success"


def test_csv_import_api_rbac(client: TestClient, db_session: Session) -> None:
    read_token = _seed_user(db_session, "readonly3@spip.local", RoleEnum.READ_ONLY.value)
    planner_token = _seed_user(db_session, "planner3@spip.local", RoleEnum.PLANNER.value)

    raw_csv = "plant_code,material_code,date,quantity,uom\nPLANT-1000,MAT-1001,2026-07-20,100,KG\n"
    csv_bytes = raw_csv.encode()
    file_obj = ("consumption.csv", io.BytesIO(csv_bytes), "text/csv")

    res_forbidden = client.post(
        "/api/v1/imports/csv?entity_type=consumption",
        files={"file": file_obj},
        headers={"Authorization": f"Bearer {read_token}"},
    )
    assert res_forbidden.status_code == 403

    file_obj2 = ("consumption.csv", io.BytesIO(csv_bytes), "text/csv")
    res_success = client.post(
        "/api/v1/imports/csv?entity_type=consumption",
        files={"file": file_obj2},
        headers={"Authorization": f"Bearer {planner_token}"},
    )
    assert res_success.status_code == 200
    assert res_success.json()["imported_records"] == 1


def test_xlsx_import_api_success(client: TestClient, db_session: Session) -> None:
    planner_token = _seed_user(db_session, "planner_xlsx@spip.local", RoleEnum.PLANNER.value)
    xlsx_bytes = _create_mock_xlsx_bytes(
        [
            ["plant_code", "material_code", "date", "quantity", "uom"],
            ["PLANT-1000", "MAT-1001", "2026-07-20", "300", "KG"],
        ]
    )
    file_obj = (
        "consumption.xlsx",
        io.BytesIO(xlsx_bytes),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    res_success = client.post(
        "/api/v1/imports/xlsx?entity_type=consumption",
        files={"file": file_obj},
        headers={"Authorization": f"Bearer {planner_token}"},
    )
    assert res_success.status_code == 200
    assert res_success.json()["imported_records"] == 1
