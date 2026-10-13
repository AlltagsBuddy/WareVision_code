"""Angebot / Kostenvoranschlag (Quote) und Angebotspositionen."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

# Dokumentarten
QUOTE_TYPE_OFFER = "offer"          # Angebot (mit Gültigkeitsdatum)
QUOTE_TYPE_ESTIMATE = "estimate"    # Kostenvoranschlag (unverbindlich, § 649 BGB)
QUOTE_TYPES = {QUOTE_TYPE_OFFER, QUOTE_TYPE_ESTIMATE}

# Status
QUOTE_STATUSES = {"draft", "sent", "accepted", "rejected", "converted"}


class Quote(BaseModel):
    """Angebot oder Kostenvoranschlag an einen Kunden."""

    __tablename__ = "quotes"

    quote_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    quote_type: Mapped[str] = mapped_column(String(20), nullable=False, default=QUOTE_TYPE_OFFER)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False
    )
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=True
    )
    quote_date: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)            # erscheint auf dem PDF
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)   # nur intern
    net_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    vat_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    # Herkunft (neue Version eines Angebots) und Ergebnis (umgewandelter Werkstattauftrag)
    previous_quote_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quotes.id", ondelete="SET NULL"), nullable=True
    )
    workshop_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workshop_orders.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    customer = relationship("Customer")
    vehicle = relationship("Vehicle")
    workshop_order = relationship("WorkshopOrder")
    items = relationship(
        "QuoteItem",
        back_populates="quote",
        cascade="all, delete-orphan",
        order_by="QuoteItem.position",
    )


class QuoteItem(BaseModel):
    """Position eines Angebots (Arbeit, Material, Leistung)."""

    __tablename__ = "quote_items"

    quote_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    item_type: Mapped[str] = mapped_column(String(20), nullable=False)  # labor, material, service
    article_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("articles.id"), nullable=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=1, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("19.00"), nullable=False)
    line_total_net: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)

    quote = relationship("Quote", back_populates="items")
