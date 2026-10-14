"""Eingangsrechnung Schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class IncomingInvoiceCreate(BaseModel):
    """Neue Eingangsrechnung anlegen."""

    supplier_name: str = Field(..., min_length=1, strip_whitespace=True)
    invoice_number: str = Field(..., min_length=1, strip_whitespace=True)
    invoice_date: date
    due_date: Optional[date] = None
    net_amount: Decimal = Field(..., ge=0)
    vat_rate: Decimal = Field(default=Decimal("19.00"), ge=0, le=100)
    vat_amount: Decimal = Field(default=Decimal("0.00"))
    gross_amount: Decimal = Field(default=Decimal("0.00"))
    category: Optional[str] = None
    notes: Optional[str] = None
    is_credit_note: bool = False  # Gutschrift/Rechnungskorrektur des Lieferanten

    @model_validator(mode="after")
    def berechne_betraege(self) -> "IncomingInvoiceCreate":
        """MwSt und Brutto automatisch aus Netto und MwSt-Satz berechnen."""
        self.vat_amount = (self.net_amount * self.vat_rate / 100).quantize(Decimal("0.01"))
        self.gross_amount = self.net_amount + self.vat_amount
        return self


class IncomingInvoiceUpdate(BaseModel):
    """Eingangsrechnung aktualisieren (alle Felder optional)."""

    supplier_name: Optional[str] = Field(None, min_length=1)
    invoice_number: Optional[str] = Field(None, min_length=1)
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    net_amount: Optional[Decimal] = Field(None, ge=0)
    vat_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    status: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None
    is_credit_note: Optional[bool] = None


class IncomingInvoiceRead(BaseModel):
    """Eingangsrechnung Ausgabe."""

    id: UUID
    supplier_name: str
    invoice_number: str
    invoice_date: date
    due_date: Optional[date] = None
    net_amount: Decimal
    vat_amount: Decimal
    gross_amount: Decimal
    vat_rate: Decimal
    status: str
    category: Optional[str] = None
    notes: Optional[str] = None
    pdf_path: Optional[str] = None
    einvoice_format: Optional[str] = None
    is_credit_note: bool = False
    original_filename: Optional[str] = None
    original_sha256: Optional[str] = None
    service_date: Optional[date] = None
    supplier_vat_id: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True
