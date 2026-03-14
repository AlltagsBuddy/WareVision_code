"""Audit logs API (admin only)."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("")
def list_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    action: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> list[dict]:
    """List audit logs (admin only)."""
    query = db.query(AuditLog)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(AuditLog.entity_id == entity_id)
    if action:
        query = query.filter(AuditLog.action == action)
    rows = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

    return [
        {
            "id": str(r.id),
            "user_id": str(r.user_id) if r.user_id else None,
            "entity_type": r.entity_type,
            "entity_id": str(r.entity_id) if r.entity_id else None,
            "action": r.action,
            "old_values": r.old_values,
            "new_values": r.new_values,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
