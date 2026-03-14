"""SQLAlchemy models."""

from app.models.base import BaseModel
from app.models.role import Role
from app.models.user import User
from app.models.customer import Customer, CustomerAddress
from app.models.manufacturer import Manufacturer, VehicleModel
from app.models.vehicle import Vehicle
from app.models.supplier import Supplier
from app.models.article_category import ArticleCategory
from app.models.article import Article
from app.models.stock_movement import StockMovement
from app.models.appointment import Appointment
from app.models.workshop_order import WorkshopOrder, WorkshopOrderItem
from app.models.maintenance_plan import MaintenancePlan, MaintenanceTask
from app.models.invoice import Invoice, InvoiceItem
from app.models.document import Document
from app.models.audit_log import AuditLog

__all__ = [
    "BaseModel",
    "Role",
    "User",
    "Customer",
    "CustomerAddress",
    "Manufacturer",
    "VehicleModel",
    "Vehicle",
    "Supplier",
    "ArticleCategory",
    "Article",
    "StockMovement",
    "Appointment",
    "WorkshopOrder",
    "WorkshopOrderItem",
    "MaintenancePlan",
    "MaintenanceTask",
    "Invoice",
    "InvoiceItem",
    "Document",
    "AuditLog",
]
