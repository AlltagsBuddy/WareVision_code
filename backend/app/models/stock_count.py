"""Inventur (Bestandsaufnahme) und Inventurpositionen."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

# Status: offen (Zählung läuft) -> abgeschlossen (gebucht, unveränderbar) oder abgebrochen
STOCK_COUNT_STATUSES = {"open", "completed", "cancelled"}


class StockCount(BaseModel):
    """Inventur zu einem Stichtag (ganzes Lager oder Teilbereich)."""

    __tablename__ = "stock_counts"

    count_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    count_date: Mapped[date] = mapped_column(Date, nullable=False)  # Stichtag
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    # Optionaler Umfang (leer = alle aktiven Artikel)
    storage_location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("storage_locations.id", ondelete="SET NULL"), nullable=True
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("article_categories.id", ondelete="SET NULL"), nullable=True
    )
    scope_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Werte zum Einkaufspreis, beim Abschluss festgeschrieben
    value_expected: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    value_counted: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    completed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items = relationship(
        "StockCountItem",
        back_populates="stock_count",
        cascade="all, delete-orphan",
        order_by="StockCountItem.sort_key",
    )


class StockCountItem(BaseModel):
    """Zählposition: ein Artikel mit Soll- und Ist-Bestand."""

    __tablename__ = "stock_count_items"

    stock_count_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stock_counts.id", ondelete="CASCADE"), nullable=False
    )
    article_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("articles.id"), nullable=False)
    # Momentaufnahme der Artikeldaten (bleibt unverändert, auch wenn der Artikel später geändert wird)
    article_number: Mapped[str] = mapped_column(String(100), nullable=False)
    article_name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(255), nullable=True)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)  # EK
    sort_key: Mapped[str] = mapped_column(String(400), nullable=False, default="")
    book_qty_at_start: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Soll-Bestand im Moment der Zählung (Buchungen während der Inventur werden so berücksichtigt)
    expected_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    counted_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    difference: Mapped[int | None] = mapped_column(Integer, nullable=True)  # beim Abschluss gesetzt
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    counted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    counted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    stock_count = relationship("StockCount", back_populates="items")
