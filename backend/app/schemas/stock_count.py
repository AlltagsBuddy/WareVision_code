"""Schemas für die Inventur."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class StockCountCreate(BaseModel):
    """Neue Inventur anlegen."""

    count_date: date
    storage_location_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    notes: Optional[str] = Field(default=None, max_length=2000)


class StockCountItemUpdate(BaseModel):
    """Zählergebnis erfassen (counted_qty = None setzt die Zählung zurück)."""

    counted_qty: Optional[int] = Field(default=None, ge=0, le=1_000_000)
    note: Optional[str] = Field(default=None, max_length=255)


class StockCountItemRead(BaseModel):
    """Zählposition."""

    id: UUID
    article_id: UUID
    article_number: str
    article_name: str
    location: Optional[str] = None
    barcode: Optional[str] = None
    unit_cost: Decimal
    book_qty_at_start: int
    expected_qty: Optional[int] = None
    counted_qty: Optional[int] = None
    difference: Optional[int] = None
    note: Optional[str] = None
    counted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StockCountRead(BaseModel):
    """Inventur (Kopf) mit Fortschritt."""

    id: UUID
    count_number: str
    count_date: date
    status: str
    scope_label: Optional[str] = None
    notes: Optional[str] = None
    value_expected: Optional[Decimal] = None
    value_counted: Optional[Decimal] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    total_items: int = 0
    counted_items: int = 0


class StockCountDetail(StockCountRead):
    """Inventur mit allen Positionen."""

    items: list[StockCountItemRead] = []
