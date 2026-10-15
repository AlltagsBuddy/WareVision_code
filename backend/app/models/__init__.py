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
from app.models.stock_reservation import StockReservation
from app.models.appointment import Appointment
from app.models.workshop_order import WorkshopOrder, WorkshopOrderItem
from app.models.maintenance_plan import MaintenancePlan, MaintenanceTask
from app.models.invoice import Invoice, InvoiceItem
from app.models.document import Document
from app.models.audit_log import AuditLog
from app.models.storage_location import StorageLocation
from app.models.app_setting import AppSetting
from app.models.labor_rate import LaborRate
from app.models.incoming_invoice import IncomingInvoice
from app.models.quote import Quote, QuoteItem
from app.models.stock_count import StockCount, StockCountItem
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.datev import DatevAccount
from app.models.archived_document import ArchivedDocument
from app.models.workshop_order_photo import WorkshopOrderPhoto
from app.models.supplier_catalog import SupplierCatalogItem

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
    "StockReservation",
    "Appointment",
    "WorkshopOrder",
    "WorkshopOrderItem",
    "MaintenancePlan",
    "MaintenanceTask",
    "Invoice",
    "InvoiceItem",
    "Document",
    "AuditLog",
    "StorageLocation",
    "AppSetting",
    "LaborRate",
    "IncomingInvoice",
    "Quote",
    "QuoteItem",
    "StockCount",
    "StockCountItem",
    "PurchaseOrder",
    "PurchaseOrderItem",
    "DatevAccount",
    "ArchivedDocument",
    "WorkshopOrderPhoto",
    "SupplierCatalogItem",
]
