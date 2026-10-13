"""Workshop order schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

VALID_STATUSES = {"new", "planned", "in_progress", "completed", "invoiced", "cancelled"}


class WorkshopOrderItemCreate(BaseModel):
    """Create workshop order item."""

    item_type: str  # labor, material, service
    article_id: Optional[UUID] = None
    description: str
    quantity: Decimal = 1
    unit: Optional[str] = None
    unit_price: Decimal = 0
    vat_rate: Decimal = 19.00


class WorkshopOrderItemRead(BaseModel):
    """Workshop order item read."""

    id: UUID
    workshop_order_id: UUID
    item_type: str
    article_id: Optional[UUID] = None
    description: str
    quantity: Decimal
    unit: Optional[str] = None
    unit_price: Decimal
    vat_rate: Decimal

    class Config:
        from_attributes = True


class WorkshopOrderCreate(BaseModel):
    """Create workshop order."""

    customer_id: UUID
    vehicle_id: UUID
    appointment_id: Optional[UUID] = None
    maintenance_plan_id: Optional[UUID] = None  # Manueller Override; None = automatisch ermitteln
    labor_rate_id: Optional[UUID] = None  # Stundenpreis für automatischen Arbeitszeit-Posten
    complaint_description: Optional[str] = None
    internal_notes: Optional[str] = None
    mileage_at_checkin: Optional[int] = Field(default=None, ge=0)
    operating_hours_at_checkin: Optional[int] = Field(default=None, ge=0)
    estimated_work_minutes: Optional[int] = Field(default=None, ge=0)


class WorkshopOrderUpdate(BaseModel):
    """Update workshop order."""

    customer_id: Optional[UUID] = None
    vehicle_id: Optional[UUID] = None
    complaint_description: Optional[str] = None
    status: Optional[str] = None
    actual_work_minutes: Optional[int] = Field(default=None, ge=0)
    internal_notes: Optional[str] = None

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: Optional[str]) -> Optional[str]:
        """Status muss ein gültiger Wert sein."""
        if v is not None and v not in VALID_STATUSES:
            raise ValueError(f"Ungültiger Status. Erlaubt: {', '.join(sorted(VALID_STATUSES))}")
        return v


class WorkshopOrderRead(BaseModel):
    """Workshop order read."""

    id: UUID
    customer_id: UUID
    vehicle_id: UUID
    appointment_id: Optional[UUID] = None
    maintenance_plan_id: Optional[UUID] = None
    maintenance_plan_name: Optional[str] = None
    order_number: str
    status: str
    complaint_description: Optional[str] = None
    internal_notes: Optional[str] = None
    mileage_at_checkin: Optional[int] = None
    actual_work_minutes: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
