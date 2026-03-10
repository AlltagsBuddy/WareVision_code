"""Article model."""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.stock_movement import StockMovement


class Article(BaseModel):
    """Article / product."""

    __tablename__ = "articles"

    article_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("article_categories.id"),
        nullable=True,
    )
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id"),
        nullable=True,
    )
    purchase_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=0, nullable=False
    )
    sales_price_b2c: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=0, nullable=False
    )
    sales_price_b2b: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=0, nullable=False
    )
    vat_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=19.00, nullable=False
    )
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    minimum_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(255), nullable=True)
    qr_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    oem_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    stock_movements = relationship("StockMovement", back_populates="article")
