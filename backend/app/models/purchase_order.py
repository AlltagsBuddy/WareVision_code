"""Bestellung beim Lieferanten (PurchaseOrder) und Bestellpositionen."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

# Status einer Bestellung
#   draft     = Entwurf (noch nicht bestellt, bearbeitbar)
#   sent      = bestellt (per E-Mail oder manuell als bestellt markiert)
#   partial   = teilweise geliefert
#   received  = vollständig geliefert
#   closed    = abgeschlossen, Restmenge wird nicht mehr geliefert
#   cancelled = storniert (nichts geliefert)
PURCHASE_ORDER_STATUSES = {"draft", "sent", "partial", "received", "closed", "cancelled"}
OPEN_STATUSES = {"draft", "sent", "partial"}


class PurchaseOrder(BaseModel):
    """Bestellung bei einem Lieferanten."""

    __tablename__ = "purchase_orders"

    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)            # erscheint auf dem PDF
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)   # nur intern
    net_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    vat_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_to_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    supplier = relationship("Supplier")
    items = relationship(
        "PurchaseOrderItem",
        back_populates="purchase_order",
        cascade="all, delete-orphan",
        order_by="PurchaseOrderItem.position",
    )

    @property
    def supplier_name(self) -> str | None:
        """Name des Lieferanten (für Listen und PDF)."""
        return self.supplier.name if self.supplier else None


class PurchaseOrderItem(BaseModel):
    """Bestellposition. Mit Artikel = wird beim Wareneingang ins Lager gebucht."""

    __tablename__ = "purchase_order_items"

    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    article_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("articles.id"), nullable=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    article_number: Mapped[str | None] = mapped_column(String(100), nullable=True)           # eigene Nr.
    supplier_article_number: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Nr. beim Lieferanten
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    received_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)  # EK netto
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("19.00"), nullable=False)
    line_total_net: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)

    purchase_order = relationship("PurchaseOrder", back_populates="items")
