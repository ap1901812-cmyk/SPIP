from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.db.models.user import RoleEnum, User, UserRole
from app.services.jobs import create_job, execute_job, get_job_by_id, retry_job


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


def test_unauthenticated_jobs_rejection(client):
    res = client.get("/api/v1/jobs")
    assert res.status_code == 401

    res_post = client.post("/api/v1/jobs", json={"job_type": "SAP_SYNC"})
    assert res_post.status_code == 401


def test_job_service_lifecycle_and_persistence(db_session: Session):
    user = _seed_test_user(db_session, "job_user@spip.local", RoleEnum.ADMIN.value)

    # 1. Create job
    job = create_job(db_session, "SAP_SYNC", user_id=user.id)
    assert job.status == "PENDING"
    assert job.job_id.startswith("JOB-")

    # 2. Execute job
    executed = execute_job(db_session, job.job_id)
    assert executed.status == "COMPLETED"
    assert executed.started_at is not None
    assert executed.completed_at is not None
    assert "synced_counts" in executed.result_json

    # 3. Fetch from DB
    fetched = get_job_by_id(db_session, job.job_id)
    assert fetched.status == "COMPLETED"


def test_durable_export_job_persistence(client, db_session: Session):
    user = _seed_test_user(db_session, "job_export@spip.local", RoleEnum.PLANNER.value)
    headers = _auth_header(user)

    # Request export job via API
    res = client.post(
        "/api/v1/reports/exports",
        json={"report_type": "planning_summary", "format": "csv"},
        headers=headers,
    )
    assert res.status_code == 200
    export_id = res.json()["export_id"]

    # Verify persisted in PostgreSQL DB
    db_job = get_job_by_id(db_session, export_id)
    assert db_job.status == "COMPLETED"
    assert db_job.binary_artifact is not None
    assert len(db_job.binary_artifact) > 0

    # Download export artifact
    res_dl = client.get(f"/api/v1/reports/exports/{export_id}/download", headers=headers)
    assert res_dl.status_code == 200
    assert "text/csv" in res_dl.headers["content-type"]


def test_job_concurrency_locking_and_retry(db_session: Session):
    user = _seed_test_user(db_session, "job_lock@spip.local", RoleEnum.ADMIN.value)
    job = create_job(db_session, "FORECAST_GENERATE", user_id=user.id)

    # Execute completes
    executed = execute_job(db_session, job.job_id)
    assert executed.status == "COMPLETED"

    # Re-executing completed job is idempotent
    second = execute_job(db_session, job.job_id)
    assert second.status == "COMPLETED"

    # Simulate failed job state
    job.status = "FAILED"
    job.error_message = "Simulated network timeout"
    db_session.commit()

    # Retry job
    retried = retry_job(db_session, job.job_id)
    assert retried.status == "COMPLETED"
    assert retried.error_message is None


def test_jobs_api_endpoints(client, db_session: Session):
    user = _seed_test_user(db_session, "job_api@spip.local", RoleEnum.ADMIN.value)
    headers = _auth_header(user)

    # 1. Trigger job via POST /api/v1/jobs
    res = client.post("/api/v1/jobs", json={"job_type": "PLANNING_RECALC"}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["job_type"] == "PLANNING_RECALC"
    assert data["status"] == "COMPLETED"
    job_id = data["job_id"]

    # 2. Get single job
    res_get = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["job_id"] == job_id

    # 3. List jobs
    res_list = client.get("/api/v1/jobs?job_type=PLANNING_RECALC", headers=headers)
    assert res_list.status_code == 200
    assert res_list.json()["total"] >= 1
