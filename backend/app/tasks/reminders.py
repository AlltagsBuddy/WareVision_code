"""Erinnerungsaufgaben: Überfällige Rechnungen ins Audit-Log schreiben."""

import logging
from datetime import date

from app.worker import celery_app

logger = logging.getLogger(__name__)

# Beschreibung für die API
TASK_META = {
    "name": "app.tasks.reminders.check_overdue_invoices",
    "label": "Überfällige Rechnungen prüfen",
    "description": "Prüft täglich alle ausgestellten Rechnungen auf Überfälligkeit und schreibt einen Audit-Log-Eintrag pro überfälliger Rechnung (ohne Mahnung).",
    "schedule": "Täglich 08:00 Uhr",
}


@celery_app.task(name="app.tasks.reminders.check_overdue_invoices", bind=True)
def check_overdue_invoices(self) -> dict:
    """Tägliche Prüfung: Überfällige Rechnungen im Audit-Log dokumentieren."""
    from app.core.database import SessionLocal
    from app.models.invoice import Invoice
    from app.services.audit import log_audit

    db = SessionLocal()
    try:
        today = date.today()
        overdue = (
            db.query(Invoice)
            .filter(
                Invoice.status.in_(["issued", "partially_paid"]),
                Invoice.due_date.isnot(None),
                Invoice.due_date < today,
                Invoice.reminder_level == 0,
            )
            .all()
        )
        count = 0
        for inv in overdue:
            days = (today - inv.due_date).days
            log_audit(
                db,
                user_id=None,
                entity_type="invoice",
                entity_id=inv.id,
                action="overdue_detected",
                new_values={
                    "invoice_number": inv.invoice_number,
                    "due_date": str(inv.due_date),
                    "days_overdue": days,
                },
            )
            count += 1
        db.commit()
        logger.info("check_overdue_invoices: %d überfällige Rechnungen gefunden", count)
        return {"task": "check_overdue_invoices", "overdue_count": count, "date": str(today)}
    finally:
        db.close()
