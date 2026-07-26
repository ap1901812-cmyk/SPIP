from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.db.models.audit import AuditLog

logger = logging.getLogger(__name__)


def record_audit_event(
    db: Session,
    action: str,
    user_id: int | None = None,
    user_email: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Records an immutable security or operational event to the audit log."""
    log_entry = AuditLog(
        user_id=user_id,
        user_email=user_email,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
    )
    db.add(log_entry)
    try:
        db.commit()
        db.refresh(log_entry)
    except Exception:
        db.rollback()
        logger.exception("Failed to write audit log entry to database.")
    return log_entry
