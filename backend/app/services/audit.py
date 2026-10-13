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
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Audit-Ereignis protokollieren (GoBD/DSGVO-konform)."""
    entry = AuditLog(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        old_values=old_values,
        new_values=new_values,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(entry)
