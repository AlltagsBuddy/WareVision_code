"""Audit logs API (admin only)."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Text, cast, select
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
    search: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> list[dict]:
    """List audit logs (admin only). search durchsucht Bereich, Aktion, Benutzer und geänderte Werte."""
    query = db.query(AuditLog)
    if search and search.strip():
        term = f"%{search.strip()}%"
        user_ids = select(User.id).where(User.email.ilike(term) | User.first_name.ilike(term) | User.last_name.ilike(term))
        query = query.filter(
            AuditLog.entity_type.ilike(term)
            | AuditLog.action.ilike(term)
            | AuditLog.user_id.in_(user_ids)
            | cast(AuditLog.old_values, Text).ilike(term)
            | cast(AuditLog.new_values, Text).ilike(term)
        )
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(AuditLog.entity_id == entity_id)
    if action:
        query = query.filter(AuditLog.action == action)
    rows = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()
    # Wer hat geändert: Name und E-Mail des Benutzers mitliefern
    ids = {r.user_id for r in rows if r.user_id}
    users = {u.id: u for u in db.query(User).filter(User.id.in_(ids)).all()} if ids else {}

    def who(uid):
        u = users.get(uid)
        if not u:
            return None
        return f"{u.first_name} {u.last_name}".strip() or u.email

    return [
        {
            "id": str(r.id),
            "user_id": str(r.user_id) if r.user_id else None,
            "user_name": who(r.user_id),
            "user_email": users[r.user_id].email if r.user_id in users else None,
            "entity_type": r.entity_type,
            "entity_id": str(r.entity_id) if r.entity_id else None,
            "action": r.action,
            "old_values": r.old_values,
            "new_values": r.new_values,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
