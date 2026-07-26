from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_safe_status_and_request_id() -> None:
    response = TestClient(app).get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-request-id"]
    assert response.headers["x-content-type-options"] == "nosniff"


def test_unknown_route_returns_safe_error() -> None:
    response = TestClient(app).get("/api/v1/unknown")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
    assert "traceback" not in response.text.lower()
