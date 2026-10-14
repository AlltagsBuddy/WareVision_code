"""Invoice and InvoiceItem models."""

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.workshop_order import WorkshopOrder
    from app.models.user import User


class Invoice(BaseModel):
    """Invoice."""

    __tablename__ = "invoices"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id"),
        nullable=False,
    )
    workshop_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workshop_orders.id"),
        nullable=True,
    )
    # GoBD: Stornorechnung referenziert die ursprüngliche Rechnung
    cancellation_of_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id"),
        nullable=True,
    )
    cancellation_invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id"),
        nullable=True,
    )
    # Rechnungskorrektur (Gutschrift des Verkäufers) referenziert die korrigierte Rechnung
    corrects_invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="SET NULL"),
        nullable=True,
    )
    # invoice = Rechnung, cancellation = Stornorechnung, correction = Rechnungskorrektur
    document_type: Mapped[str] = mapped_column(String(20), default="invoice", server_default="invoice", nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Leistungsdatum (Pflichtangabe nach § 14 Abs. 4 Nr. 6 UStG)
    service_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # draft, issued, partially_paid, paid, cancelled
    currency: Mapped[str] = mapped_column(String(10), default="EUR", nullable=False)
    net_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    vat_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    zugferd_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    reminder_level: Mapped[int] = mapped_column(default=0, nullable=False)  # 0=none, 1=1.Mahnung, 2=2., 3=3.
    reminder_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    customer = relationship("Customer", back_populates="invoices")
    workshop_order = relationship("WorkshopOrder", back_populates="invoices")
    cancellation_of = relationship("Invoice", foreign_keys=[cancellation_of_id], remote_side="Invoice.id", backref="cancellation_invoice_rel")
    corrects_invoice = relationship("Invoice", foreign_keys=[corrects_invoice_id], remote_side="Invoice.id")
    items = relationship(
        "InvoiceItem",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )

    @property
    def referenced_invoice(self) -> "Invoice | None":
        """Bezugsrechnung einer Stornorechnung oder Rechnungskorrektur (§ 31 Abs. 5 UStDV)."""
        return self.cancellation_of or self.corrects_invoice


class InvoiceItem(BaseModel):
    """Invoice item."""

    __tablename__ = "invoice_items"

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
    )
    article_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("articles.id"),
        nullable=True,
    )
    workshop_order_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workshop_order_items.id"),
        nullable=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=1, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=19.00, nullable=False)
    line_total_net: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=0, nullable=False
    )
    # Rechnungskorrektur: Bezug auf die korrigierte Originalposition und Rückbuchung ins Lager
    corrects_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoice_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    returned_to_stock: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)

    invoice = relationship("Invoice", back_populates="items")
