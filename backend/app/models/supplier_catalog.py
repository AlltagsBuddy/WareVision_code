"""Lieferanten-Artikeldaten (Katalog): Vorschläge zum Anlegen von Artikeln per Barcode-Scan.

Quellen: Artikeldatei des Lieferanten (CSV/Excel), Positionen aus Lieferanten-E-Rechnungen.
Ein Katalogeintrag ist kein Lagerartikel – er füllt nur das Artikel-Formular vor.
"""

import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class SupplierCatalogItem(BaseModel):
    __tablename__ = "supplier_catalog_items"
    __table_args__ = (
        Index("ix_supplier_catalog_barcode", "barcode"),
        Index("ix_supplier_catalog_supplier_number", "supplier_name", "supplier_article_number"),
    )

    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True
    )
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # import | einvoice
    source_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Dateiname / Rechnungsnummer
    barcode: Mapped[str | None] = mapped_column(String(255), nullable=True)
    supplier_article_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(150), nullable=True)
    manufacturer_part_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    retail_price_net: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    vat_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)

    supplier = relationship("Supplier")
