"""Audit logging service for GoBD/DSGVO compliance."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def log_audit(
    db: Session,
    *,
    user_id: UUID | None = None,
    entity_type: str,
    entity_id: UUID | None = None,
    action: str,
    old_values: dict | None = None,
    new_values: dict | None = None,
) -> None:
    """Log an audit event."""
    entry = AuditLog(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        old_values=old_values,
        new_values=new_values,
    )
    db.add(entry)
