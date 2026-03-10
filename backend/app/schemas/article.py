"""Article schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ArticleCreate(BaseModel):
    """Create article."""

    article_number: str
    name: str
    description: Optional[str] = None
    category_id: Optional[UUID] = None
    supplier_id: Optional[UUID] = None
    purchase_price: Decimal = 0
    sales_price_b2c: Decimal = 0
    sales_price_b2b: Decimal = 0
    vat_rate: Decimal = 19.00
    minimum_stock: int = 0
    barcode: Optional[str] = None
    qr_code: Optional[str] = None
    oem_number: Optional[str] = None
    location_label: Optional[str] = None


class ArticleUpdate(BaseModel):
    """Update article."""

    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[UUID] = None
    supplier_id: Optional[UUID] = None
    purchase_price: Optional[Decimal] = None
    sales_price_b2c: Optional[Decimal] = None
    sales_price_b2b: Optional[Decimal] = None
    vat_rate: Optional[Decimal] = None
    minimum_stock: Optional[int] = None
    barcode: Optional[str] = None
    qr_code: Optional[str] = None
    oem_number: Optional[str] = None
    location_label: Optional[str] = None
    is_active: Optional[bool] = None


class ArticleRead(BaseModel):
    """Article read."""

    id: UUID
    article_number: str
    name: str
    description: Optional[str] = None
    category_id: Optional[UUID] = None
    supplier_id: Optional[UUID] = None
    purchase_price: Decimal
    sales_price_b2c: Decimal
    sales_price_b2b: Decimal
    vat_rate: Decimal
    stock_quantity: int
    minimum_stock: int
    barcode: Optional[str] = None
    qr_code: Optional[str] = None
    oem_number: Optional[str] = None
    location_label: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
