from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.errors import ServiceUnavailableError
from app.db.session import get_db_session
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready", response_model=HealthResponse)
def readiness(session: Session = Depends(get_db_session)) -> HealthResponse:
    try:
        session.execute(text("SELECT 1"))
    except Exception as exc:
        raise ServiceUnavailableError("Service dependency is unavailable.") from exc
    return HealthResponse(status="ready")
