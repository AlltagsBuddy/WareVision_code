"""Invoice schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class InvoiceItemCreate(BaseModel):
    """Create invoice item."""

    description: str
    quantity: Decimal = 1
    unit: Optional[str] = None
    unit_price: Decimal = 0
    vat_rate: Decimal = 19.00


class InvoiceCreate(BaseModel):
    """Create invoice."""

    customer_id: UUID
    workshop_order_id: Optional[UUID] = None
    invoice_date: date
    due_date: Optional[date] = None
    notes: Optional[str] = None
    items: list[InvoiceItemCreate] = []


class InvoiceItemRead(BaseModel):
    """Invoice item read."""

    id: UUID
    description: str
    quantity: Decimal
    unit: Optional[str] = None
    unit_price: Decimal
    vat_rate: Decimal
    line_total_net: Decimal

    class Config:
        from_attributes = True


class InvoiceRead(BaseModel):
    """Invoice read."""

    id: UUID
    customer_id: UUID
    workshop_order_id: Optional[UUID] = None
    invoice_number: str
    invoice_date: date
    due_date: Optional[date] = None
    status: str
    currency: str
    net_amount: Decimal
    vat_amount: Decimal
    gross_amount: Decimal
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
