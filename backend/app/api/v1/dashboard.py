"""Dashboard API - aggregated stats for overview."""

from datetime import date, datetime, timedelta, timezone

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.appointment import Appointment
from app.models.customer import Customer
from app.models.document import Document
from app.models.invoice import Invoice
from app.models.user import User
from app.models.workshop_order import WorkshopOrder

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
def get_dashboard_stats(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Aggregated stats for dashboard (customers, orders, appointments, invoices, etc.)."""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    week_start_dt = datetime.combine(week_start, datetime.min.time()).replace(tzinfo=timezone.utc)
    week_end_dt = datetime.combine(week_end, datetime.max.time().replace(microsecond=0)).replace(tzinfo=timezone.utc)
    today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
    today_end = datetime.combine(today, datetime.max.time().replace(microsecond=0)).replace(tzinfo=timezone.utc)

    customers = db.query(func.count(Customer.id)).filter(Customer.is_active == True).scalar() or 0
    documents = db.query(func.count(Document.id)).scalar() or 0
    workshop_orders = db.query(func.count(WorkshopOrder.id)).scalar() or 0
    invoices = db.query(func.count(Invoice.id)).scalar() or 0
    overdue_invoices = (
        db.query(func.count(Invoice.id))
        .filter(
            Invoice.status.in_(["issued", "partially_paid"]),
            Invoice.due_date.isnot(None),
            Invoice.due_date < today,
        )
        .scalar()
        or 0
    )
    appointments_week = (
        db.query(func.count(Appointment.id))
        .filter(
            Appointment.status != "cancelled",
            Appointment.starts_at <= week_end_dt,
            Appointment.ends_at >= week_start_dt,
        )
        .scalar()
        or 0
    )
    appointments_today = (
        db.query(func.count(Appointment.id))
        .filter(
            Appointment.status != "cancelled",
            Appointment.starts_at <= today_end,
            Appointment.ends_at >= today_start,
        )
        .scalar()
        or 0
    )

    from app.models.article import Article
    from app.models.maintenance_plan import MaintenancePlan

    low_stock = (
        db.query(func.count(Article.id))
        .filter(Article.minimum_stock > 0, Article.stock_quantity < Article.minimum_stock)
        .scalar()
        or 0
    )
    maintenance_plans = db.query(func.count(MaintenancePlan.id)).scalar() or 0

    return {
        "customers": customers,
        "documents": documents,
        "workshop_orders": workshop_orders,
        "appointments_week": appointments_week,
        "appointments_today": appointments_today,
        "invoices": invoices,
        "overdue_invoices": overdue_invoices,
        "low_stock": low_stock,
        "maintenance_plans": maintenance_plans,
    }
