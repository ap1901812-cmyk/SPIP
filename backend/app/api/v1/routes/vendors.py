from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models.domain import Vendor
from app.db.models.user import User
from app.schemas.domain import VendorResponse

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.get("", response_model=list[VendorResponse])
def list_vendors(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[VendorResponse]:
    vendors = db.query(Vendor).all()
    return [VendorResponse.model_validate(v) for v in vendors]
