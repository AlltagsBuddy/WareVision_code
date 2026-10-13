"""Invoice schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class InvoiceItemCreate(BaseModel):
    """Create invoice item."""

    description: str = Field(..., min_length=1, strip_whitespace=True)
    article_id: Optional[UUID] = None
    quantity: Decimal = 1
    unit: Optional[str] = None
    unit_price: Decimal = 0
    vat_rate: Decimal = Decimal("19.00")

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, v: Decimal) -> Decimal:
        """Menge muss größer als 0 sein."""
        if v <= 0:
            raise ValueError("Menge muss größer als 0 sein")
        return v

    @field_validator("unit_price")
    @classmethod
    def unit_price_non_negative(cls, v: Decimal) -> Decimal:
        """Einzelpreis darf nicht negativ sein."""
        if v < 0:
            raise ValueError("Einzelpreis darf nicht negativ sein")
        return v

    @field_validator("vat_rate")
    @classmethod
    def vat_rate_valid(cls, v: Decimal) -> Decimal:
        """MwSt-Satz muss zwischen 0 und 100 liegen."""
        if v < 0 or v > 100:
            raise ValueError("MwSt-Satz muss zwischen 0 und 100 liegen")
        return v


class InvoiceCreate(BaseModel):
    """Create invoice."""

    customer_id: UUID
    workshop_order_id: Optional[UUID] = None
    invoice_date: date
    # Leistungsdatum (§ 14 Abs. 4 Nr. 6 UStG); leer = Rechnungsdatum
    service_date: Optional[date] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None
    items: list[InvoiceItemCreate] = []

    @field_validator("items")
    @classmethod
    def items_not_empty(cls, v: list) -> list:
        """Rechnung muss mindestens eine Position enthalten (bei manueller Eingabe)."""
        return v

    def model_post_init(self, __context: object) -> None:
        """Fälligkeitsdatum darf nicht vor dem Rechnungsdatum liegen."""
        if self.due_date and self.due_date < self.invoice_date:
            raise ValueError("Fälligkeitsdatum darf nicht vor dem Rechnungsdatum liegen")


class InvoiceItemRead(BaseModel):
    """Invoice item read."""

    id: UUID
    article_id: Optional[UUID] = None
    workshop_order_item_id: Optional[UUID] = None
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
    cancellation_of_id: Optional[UUID] = None
    cancellation_invoice_id: Optional[UUID] = None
    invoice_number: str
    invoice_date: date
    service_date: Optional[date] = None
    due_date: Optional[date] = None
    status: str
    currency: str
    net_amount: Decimal
    vat_amount: Decimal
    gross_amount: Decimal
    notes: Optional[str] = None
    reminder_level: int = 0
    reminder_date: Optional[date] = None
    created_at: datetime

    class Config:
        from_attributes = True
