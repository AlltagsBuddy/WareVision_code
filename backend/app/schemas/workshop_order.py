"""Workshop order schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class WorkshopOrderItemCreate(BaseModel):
    """Create workshop order item."""

    item_type: str  # labor, material, service
    article_id: Optional[UUID] = None
    description: str
    quantity: Decimal = 1
    unit: Optional[str] = None
    unit_price: Decimal = 0
    vat_rate: Decimal = 19.00


class WorkshopOrderCreate(BaseModel):
    """Create workshop order."""

    customer_id: UUID
    vehicle_id: UUID
    appointment_id: Optional[UUID] = None
    complaint_description: Optional[str] = None
    internal_notes: Optional[str] = None
    mileage_at_checkin: Optional[int] = None
    operating_hours_at_checkin: Optional[int] = None
    estimated_work_minutes: Optional[int] = None


class WorkshopOrderRead(BaseModel):
    """Workshop order read."""

    id: UUID
    customer_id: UUID
    vehicle_id: UUID
    order_number: str
    status: str
    complaint_description: Optional[str] = None
    internal_notes: Optional[str] = None
    mileage_at_checkin: Optional[int] = None
    actual_work_minutes: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
