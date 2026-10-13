"""Wartungsplan-Prüfung: Fahrzeuge mit überfälligen Wartungsintervallen."""

import calendar
import logging
from datetime import date

from app.worker import celery_app

logger = logging.getLogger(__name__)

TASK_META = {
    "name": "app.tasks.maintenance_check.check_maintenance_intervals",
    "label": "Wartungsintervalle prüfen",
    "description": "Prüft wöchentlich alle aktiven Fahrzeuge auf überfällige Wartungsintervalle (laut Wartungsplan des Herstellers) und schreibt Audit-Log-Einträge.",
    "schedule": "Montags 07:00 Uhr",
}


def _add_months(d: date, months: int) -> date:
    """Datum um n Monate verschieben (monatsgenau)."""
    total_months = d.month - 1 + months
    year = d.year + total_months // 12
    month = total_months % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


@celery_app.task(name="app.tasks.maintenance_check.check_maintenance_intervals", bind=True)
def check_maintenance_intervals(self) -> dict:
    """Wöchentliche Prüfung: Fahrzeuge mit überfälligen Wartungsintervallen."""
    from app.core.database import SessionLocal
    from app.models.vehicle import Vehicle
    from app.models.workshop_order import WorkshopOrder
    from app.models.maintenance_plan import MaintenancePlan
    from app.services.audit import log_audit

    db = SessionLocal()
    try:
        today = date.today()
        vehicles = (
            db.query(Vehicle)
            .filter(Vehicle.is_active == True)  # noqa: E712
            .all()
        )
        count = 0
        for vehicle in vehicles:
            # Passende Wartungspläne ermitteln
            plans_query = db.query(MaintenancePlan)
            if vehicle.vehicle_model_id:
                plans_query = plans_query.filter(
                    MaintenancePlan.vehicle_model_id == vehicle.vehicle_model_id
                )
            elif vehicle.manufacturer_id:
                plans_query = plans_query.filter(
                    MaintenancePlan.manufacturer_id == vehicle.manufacturer_id,
                    MaintenancePlan.vehicle_model_id.is_(None),
                )
            else:
                continue
            plans = plans_query.all()
            if not plans:
                continue

            # Letzten abgeschlossenen Werkstattauftrag ermitteln
            last_order = (
                db.query(WorkshopOrder)
                .filter(
                    WorkshopOrder.vehicle_id == vehicle.id,
                    WorkshopOrder.status.in_(["completed", "invoiced"]),
                )
                .order_by(WorkshopOrder.updated_at.desc())
                .first()
            )

            for plan in plans:
                if not plan.interval_months:
                    continue

                if last_order:
                    last_date = (
                        last_order.updated_at.date()
                        if hasattr(last_order.updated_at, "date")
                        else last_order.updated_at
                    )
                    due_date = _add_months(last_date, plan.interval_months)
                    if due_date > today:
                        continue
                    last_service_str = str(last_date)
                    due_since_str = str(due_date)
                else:
                    last_service_str = None
                    due_since_str = "noch nie gewartet"

                log_audit(
                    db,
                    user_id=None,
                    entity_type="vehicle",
                    entity_id=vehicle.id,
                    action="maintenance_due",
                    new_values={
                        "license_plate": vehicle.license_plate or str(vehicle.id),
                        "plan_name": plan.name,
                        "interval_months": plan.interval_months,
                        "last_service_date": last_service_str,
                        "due_since": due_since_str,
                    },
                )
                count += 1

        db.commit()
        logger.info("check_maintenance_intervals: %d überfällige Wartungen gefunden", count)
        return {"task": "check_maintenance_intervals", "due_count": count, "date": str(today)}
    finally:
        db.close()
