"""Main API router."""

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    users,
    customers,
    vehicles,
    articles,
    manufacturers,
    stock,
    workshop_orders,
    appointments,
    invoices,
    documents,
    maintenance,
    settings,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(customers.router)
api_router.include_router(vehicles.router)
api_router.include_router(articles.router)
api_router.include_router(manufacturers.router)
api_router.include_router(stock.router)
api_router.include_router(workshop_orders.router)
api_router.include_router(appointments.router)
api_router.include_router(invoices.router)
api_router.include_router(documents.router)
api_router.include_router(maintenance.router)
api_router.include_router(settings.router)
