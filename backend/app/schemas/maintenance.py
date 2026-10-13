"""Maintenance plan schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class MaintenanceTaskCreate(BaseModel):
    """Create maintenance task."""

    name: str
    description: Optional[str] = None
    sort_order: int = 0
    article_id: Optional[UUID] = None
    quantity: Decimal = Decimal("1")
    unit: Optional[str] = "Stück"


class MaintenanceTaskRead(BaseModel):
    """Maintenance task read."""

    id: UUID
    maintenance_plan_id: UUID
    name: str
    description: Optional[str] = None
    sort_order: int
    article_id: Optional[UUID] = None
    article_name: Optional[str] = None
    article_number: Optional[str] = None
    quantity: Decimal = Decimal("1")
    unit: Optional[str] = None

    class Config:
        from_attributes = True


class MaintenanceTaskUpdate(BaseModel):
    """Wartungsaufgabe aktualisieren – alle Felder optional."""

    name: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None
    article_id: Optional[UUID] = None
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None


class MaintenancePlanCreate(BaseModel):
    """Create maintenance plan."""

    manufacturer_id: UUID
    vehicle_model_id: Optional[UUID] = None
    name: str
    description: Optional[str] = None
    interval_km: Optional[int] = None
    interval_hours: Optional[int] = None
    interval_months: Optional[int] = None


class MaintenancePlanUpdate(BaseModel):
    """Wartungsplan aktualisieren – alle Felder optional."""

    name: Optional[str] = None
    description: Optional[str] = None
    interval_km: Optional[int] = None
    interval_hours: Optional[int] = None
    interval_months: Optional[int] = None


class MaintenancePlanRead(BaseModel):
    """Maintenance plan read."""

    id: UUID
    manufacturer_id: UUID
    vehicle_model_id: Optional[UUID] = None
    document_id: Optional[UUID] = None
    document_filename: Optional[str] = None
    name: str
    description: Optional[str] = None
    interval_km: Optional[int] = None
    interval_hours: Optional[int] = None
    interval_months: Optional[int] = None
    created_at: datetime

    @classmethod
    def from_orm_with_document(cls, plan: object) -> "MaintenancePlanRead":
        """ORM-Objekt in Schema umwandeln und Dokumentname befüllen."""
        doc_filename = None
        if hasattr(plan, "document") and plan.document:
            doc_filename = getattr(plan.document, "filename", None)
        obj = cls.model_validate(plan)
        obj.document_filename = doc_filename
        return obj

    class Config:
        from_attributes = True
