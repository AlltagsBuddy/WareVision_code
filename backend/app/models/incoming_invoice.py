"""Eingangsrechnung (Kreditorenrechnung) – Rechnungen vom Lieferanten."""

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class IncomingInvoice(BaseModel):
    """Eingangsrechnung von Lieferanten oder Dienstleistern."""

    __tablename__ = "incoming_invoices"

    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(100), nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    net_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    vat_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("19.00"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    # z. B. "Ersatzteile", "Werkzeug", "Miete", "Strom", "Dienstleistung"
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Importierte E-Rechnung: Format und unverändertes Original (GoBD)
    # Gutschrift/Rechnungskorrektur des Lieferanten (wird in DATEV umgekehrt gebucht)
    is_credit_note: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    einvoice_format: Mapped[str | None] = mapped_column(String(30), nullable=True)  # zugferd, xrechnung_cii, xrechnung_ubl
    original_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    service_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    supplier_vat_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    creator = relationship("User", foreign_keys=[created_by])
