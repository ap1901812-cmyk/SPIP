from __future__ import annotations

import csv
import io

import openpyxl
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.db.models.domain import Material, Plant
from app.db.models.user import RoleEnum, User, UserRole


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


def test_unauthenticated_reporting_rejection(client):
    res = client.get("/api/v1/reports")
    assert res.status_code == 401

    res_post = client.post(
        "/api/v1/reports/exports",
        json={"report_type": "planning_summary", "format": "csv"},
    )
    assert res_post.status_code == 401


def test_invalid_report_filters_and_formats(client, db_session: Session):
    user = _seed_test_user(db_session, "rep_invalid@spip.local", RoleEnum.PLANNER.value)
    headers = _auth_header(user)

    # Invalid report type
    res_bad_type = client.get("/api/v1/reports?report_type=invalid_type", headers=headers)
    assert res_bad_type.status_code == 400
    assert "Unsupported report type" in res_bad_type.json()["message"]

    # Invalid export format (Pydantic schema validation returns 422)
    res_bad_fmt = client.post(
        "/api/v1/reports/exports",
        json={"report_type": "planning_summary", "format": "doc"},
        headers=headers,
    )
    assert res_bad_fmt.status_code == 422


def test_reporting_preview_dataset(client, db_session: Session):
    user = _seed_test_user(db_session, "rep_preview@spip.local", RoleEnum.PLANNER.value)
    headers = _auth_header(user)

    plant = Plant(code="PLANT-REP", name="Reporting Plant")
    mat = Material(code="MAT-REP", description="Reporting Mat", base_uom="KG")
    db_session.add_all([plant, mat])
    db_session.commit()

    res = client.get(
        "/api/v1/reports?report_type=planning_summary&plant_code=PLANT-REP",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "Planning Summary"
    assert "Plant Code" in data["headers"]
    assert data["total_records"] == 1
    assert data["rows"][0][0] == "PLANT-REP"


def test_direct_csv_and_xlsx_download(client, db_session: Session):
    user = _seed_test_user(db_session, "rep_dl@spip.local", RoleEnum.PLANNER.value)
    headers = _auth_header(user)

    plant = Plant(code="PLANT-DL", name="DL Plant")
    mat = Material(code="MAT-DL", description="DL Mat", base_uom="KG")
    db_session.add_all([plant, mat])
    db_session.commit()

    # 1. Test CSV Download
    res_csv = client.get(
        "/api/v1/reports/download?report_type=planning_summary&format=csv&plant_code=PLANT-DL",
        headers=headers,
    )
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert 'attachment; filename="planning_summary_' in res_csv.headers["content-disposition"]

    csv_reader = csv.reader(io.StringIO(res_csv.text))
    rows = list(csv_reader)
    assert len(rows) == 2  # Header + 1 data row
    assert rows[0][0] == "Plant Code"
    assert rows[1][0] == "PLANT-DL"

    # 2. Test XLSX Download
    res_xlsx = client.get(
        "/api/v1/reports/download?report_type=planning_summary&format=xlsx&plant_code=PLANT-DL",
        headers=headers,
    )
    assert res_xlsx.status_code == 200
    assert "openxmlformats-officedocument" in res_xlsx.headers["content-type"]
    assert 'attachment; filename="planning_summary_' in res_xlsx.headers["content-disposition"]

    wb = openpyxl.load_workbook(io.BytesIO(res_xlsx.content))
    ws = wb.active
    assert ws.title == "Planning Summary"
    assert ws.cell(row=1, column=1).value == "Plant Code"
    assert ws.cell(row=2, column=1).value == "PLANT-DL"


def test_async_export_job_workflow_and_isolation(client, db_session: Session):
    u1 = _seed_test_user(db_session, "exp_u1@spip.local", RoleEnum.PLANNER.value)
    u2 = _seed_test_user(db_session, "exp_u2@spip.local", RoleEnum.READ_ONLY.value)

    h1 = _auth_header(u1)
    h2 = _auth_header(u2)

    # User 1 submits export request
    res_job = client.post(
        "/api/v1/reports/exports",
        json={"report_type": "planning_summary", "format": "xlsx"},
        headers=h1,
    )
    assert res_job.status_code == 200
    job_data = res_job.json()
    assert job_data["export_id"].startswith("EXP-")
    assert job_data["status"] == "COMPLETED"

    export_id = job_data["export_id"]

    # User 2 tries to download User 1's export (Forbidden 403)
    res_forbidden = client.get(f"/api/v1/reports/exports/{export_id}/download", headers=h2)
    assert res_forbidden.status_code == 403

    # User 1 downloads export
    res_ok = client.get(f"/api/v1/reports/exports/{export_id}/download", headers=h1)
    assert res_ok.status_code == 200
    assert "openxmlformats-officedocument" in res_ok.headers["content-type"]

    wb = openpyxl.load_workbook(io.BytesIO(res_ok.content))
    assert wb.active is not None
