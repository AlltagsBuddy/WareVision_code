"""Celery Worker-Konfiguration und Beat-Schedule."""

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "warevision",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.reminders", "app.tasks.maintenance_check"],
)

celery_app.conf.timezone = "Europe/Berlin"
celery_app.conf.enable_utc = True
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.result_expires = 60 * 60 * 24  # 24 Stunden

celery_app.conf.beat_schedule = {
    # Täglich um 08:00 Uhr: überfällige Rechnungen prüfen
    "check-overdue-invoices-daily": {
        "task": "app.tasks.reminders.check_overdue_invoices",
        "schedule": crontab(hour=8, minute=0),
    },
    # Montags um 07:00 Uhr: Wartungsintervalle prüfen
    "check-maintenance-intervals-weekly": {
        "task": "app.tasks.maintenance_check.check_maintenance_intervals",
        "schedule": crontab(hour=7, minute=0, day_of_week=1),
    },
}
