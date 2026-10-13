"""Main API router."""

from fastapi import APIRouter

from app.api.v1 import (
    accounting,
    auth,
    dashboard,
    users,
    customers,
    vehicles,
    articles,
    article_categories,
    suppliers,
    manufacturers,
    stock,
    storage_locations,
    workshop_orders,
    appointments,
    invoices,
    incoming_invoices,
    documents,
    maintenance,
    settings,
    audit,
    tasks,
    labor_rates,
    quotes,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(accounting.router)
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(users.router)
api_router.include_router(customers.router)
api_router.include_router(vehicles.router)
api_router.include_router(articles.router)
api_router.include_router(article_categories.router)
api_router.include_router(suppliers.router)
api_router.include_router(manufacturers.router)
api_router.include_router(stock.router)
api_router.include_router(storage_locations.router)
api_router.include_router(workshop_orders.router)
api_router.include_router(appointments.router)
api_router.include_router(invoices.router)
api_router.include_router(incoming_invoices.router)
api_router.include_router(documents.router)
api_router.include_router(maintenance.router)
api_router.include_router(settings.router)
api_router.include_router(audit.router)
api_router.include_router(tasks.router)
api_router.include_router(labor_rates.router)
api_router.include_router(quotes.router)
