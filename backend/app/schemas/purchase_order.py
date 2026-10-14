"""Schemas für das Bestellwesen (Bestellungen beim Lieferanten, Wareneingang, Bestellvorschlag)."""

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class PurchaseOrderItemIn(BaseModel):
    """Bestellposition (Eingabe). Ohne Artikel = freie Position (wird nicht ins Lager gebucht)."""

    article_id: Optional[UUID] = None
    description: str = Field(..., min_length=1)
    supplier_article_number: Optional[str] = Field(default=None, max_length=100)
    quantity: int = Field(..., ge=1, le=100000)
    unit: Optional[str] = Field(default=None, max_length=50)
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

    @field_validator("unit_price")
    @classmethod
    def price_not_negative(cls, v: Decimal) -> Decimal:
        """Einkaufspreis darf nicht negativ sein; auf Cent runden."""
        if v < 0:
            raise ValueError("Einkaufspreis darf nicht negativ sein")
        return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @field_validator("vat_rate")
    @classmethod
    def vat_rate_valid(cls, v: Decimal) -> Decimal:
        """MwSt-Satz zwischen 0 und 100."""
        if v < 0 or v > 100:
            raise ValueError("MwSt-Satz muss zwischen 0 und 100 liegen")
        return v


class PurchaseOrderIn(BaseModel):
    """Bestellung anlegen oder (im Entwurf) vollständig ersetzen."""

    supplier_id: UUID
    order_date: date
    expected_date: Optional[date] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    items: list[PurchaseOrderItemIn] = Field(..., min_length=1)

    @model_validator(mode="after")
    def check_dates(self) -> "PurchaseOrderIn":
        """Liefertermin darf nicht vor dem Bestelldatum liegen."""
        if self.expected_date and self.expected_date < self.order_date:
            raise ValueError("Der Liefertermin darf nicht vor dem Bestelldatum liegen")
        return self


class PurchaseOrderSendEmailIn(BaseModel):
    """E-Mail-Versand an den Lieferanten."""

    recipient_email: Optional[str] = None


class ReceiptLineIn(BaseModel):
    """Gelieferte Menge einer Position."""

    item_id: UUID
    quantity: int = Field(..., ge=0, le=100000)


class PurchaseOrderReceiveIn(BaseModel):
    """Wareneingang buchen (auch Teillieferung)."""

    lines: list[ReceiptLineIn] = Field(..., min_length=1)
    delivery_note: Optional[str] = Field(default=None, max_length=100)  # Lieferschein-Nr.
    update_purchase_price: bool = False  # EK-Preis im Artikel auf den Bestellpreis setzen


class PurchaseOrderItemRead(BaseModel):
    """Bestellposition (Ausgabe)."""

    id: UUID
    position: int
    article_id: Optional[UUID] = None
    description: str
    article_number: Optional[str] = None
    supplier_article_number: Optional[str] = None
    quantity: int
    received_quantity: int
    unit: Optional[str] = None
    unit_price: Decimal
    vat_rate: Decimal
    line_total_net: Decimal

    class Config:
        from_attributes = True


class PurchaseOrderRead(BaseModel):
    """Bestellung (Ausgabe)."""

    id: UUID
    order_number: str
    supplier_id: UUID
    supplier_name: Optional[str] = None
    status: str
    order_date: date
    expected_date: Optional[date] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    net_amount: Decimal
    vat_amount: Decimal
    gross_amount: Decimal
    sent_at: Optional[datetime] = None
    sent_to_email: Optional[str] = None
    created_at: datetime
    items: list[PurchaseOrderItemRead] = []

    class Config:
        from_attributes = True


class SuggestionItem(BaseModel):
    """Ein Artikel im Bestellvorschlag."""

    article_id: UUID
    article_number: str
    name: str
    supplier_article_number: Optional[str] = None
    stock_quantity: int
    reserved_quantity: int
    on_order_quantity: int
    minimum_stock: int
    target_stock: Optional[int] = None
    suggested_quantity: int
    unit_price: Decimal
    vat_rate: Decimal


class SuggestionGroup(BaseModel):
    """Bestellvorschlag je Lieferant (supplier_id leer = Artikel ohne Lieferant)."""

    supplier_id: Optional[UUID] = None
    supplier_name: str
    supplier_email: Optional[str] = None
    items: list[SuggestionItem]
