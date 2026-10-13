"""Schemas für Angebote / Kostenvoranschläge."""

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class QuoteItemIn(BaseModel):
    """Angebotsposition (Eingabe)."""

    item_type: Literal["labor", "material", "service"] = "service"
    article_id: Optional[UUID] = None
    description: str = Field(..., min_length=1)
    quantity: Decimal = Decimal("1")
    unit: Optional[str] = None
    unit_price: Decimal = Decimal("0")
    vat_rate: Decimal = Decimal("19.00")

    @field_validator("description")
    @classmethod
    def description_not_blank(cls, v: str) -> str:
        """Beschreibung darf nicht leer sein."""
        v = v.strip()
        if not v:
            raise ValueError("Beschreibung darf nicht leer sein")
        return v

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, v: Decimal) -> Decimal:
        """Menge muss größer als 0 sein."""
        if v <= 0:
            raise ValueError("Menge muss größer als 0 sein")
        return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @field_validator("unit_price")
    @classmethod
    def price_not_negative(cls, v: Decimal) -> Decimal:
        """Einzelpreis darf nicht negativ sein; auf Cent runden (wie in der Datenbank gespeichert)."""
        if v < 0:
            raise ValueError("Einzelpreis darf nicht negativ sein")
        return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @field_validator("vat_rate")
    @classmethod
    def vat_rate_valid(cls, v: Decimal) -> Decimal:
        """MwSt-Satz zwischen 0 und 100."""
        if v < 0 or v > 100:
            raise ValueError("MwSt-Satz muss zwischen 0 und 100 liegen")
        return v


class QuoteIn(BaseModel):
    """Angebot anlegen oder (im Entwurf) vollständig ersetzen."""

    quote_type: Literal["offer", "estimate"] = "offer"
    customer_id: UUID
    vehicle_id: Optional[UUID] = None
    quote_date: date
    valid_until: Optional[date] = None
    subject: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    items: list[QuoteItemIn] = Field(..., min_length=1)

    @model_validator(mode="after")
    def check_dates(self) -> "QuoteIn":
        """Gültig-bis darf nicht vor dem Angebotsdatum liegen."""
        if self.valid_until and self.valid_until < self.quote_date:
            raise ValueError("„Gültig bis“ darf nicht vor dem Angebotsdatum liegen")
        return self


class QuoteStatusIn(BaseModel):
    """Statuswechsel."""

    status: Literal["sent", "accepted", "rejected"]


class QuoteConvertIn(BaseModel):
    """Umwandlung in einen Werkstattauftrag."""

    vehicle_id: Optional[UUID] = None  # Pflicht, wenn das Angebot kein Fahrzeug hat
    complaint_description: Optional[str] = None


class QuoteSendEmailIn(BaseModel):
    """E-Mail-Versand."""

    recipient_email: Optional[str] = None


class QuoteItemRead(BaseModel):
    """Angebotsposition (Ausgabe)."""

    id: UUID
    position: int
    item_type: str
    article_id: Optional[UUID] = None
    description: str
    quantity: Decimal
    unit: Optional[str] = None
    unit_price: Decimal
    vat_rate: Decimal
    line_total_net: Decimal

    class Config:
        from_attributes = True


class QuoteRead(BaseModel):
    """Angebot (Ausgabe)."""

    id: UUID
    quote_number: str
    quote_type: str
    status: str
    customer_id: UUID
    vehicle_id: Optional[UUID] = None
    quote_date: date
    valid_until: Optional[date] = None
    subject: Optional[str] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    net_amount: Decimal
    vat_amount: Decimal
    gross_amount: Decimal
    previous_quote_id: Optional[UUID] = None
    workshop_order_id: Optional[UUID] = None
    created_at: datetime
    items: list[QuoteItemRead] = []

    class Config:
        from_attributes = True
