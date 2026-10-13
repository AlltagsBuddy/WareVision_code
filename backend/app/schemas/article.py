"""Article schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ArticleCreate(BaseModel):
    """Create article."""

    article_number: str = Field(..., min_length=1, strip_whitespace=True)
    name: str = Field(..., min_length=1, strip_whitespace=True)
    description: Optional[str] = None
    category_id: Optional[UUID] = None
    supplier_id: Optional[UUID] = None
    purchase_price: Decimal = Field(default=0, ge=0)
    sales_price_b2c: Decimal = Field(default=0, ge=0)
    sales_price_b2b: Decimal = Field(default=0, ge=0)
    vat_rate: Decimal = Field(default=Decimal("19.00"), ge=0, le=100)
    minimum_stock: int = Field(default=0, ge=0)
    barcode: Optional[str] = None
    qr_code: Optional[str] = None
    oem_number: Optional[str] = None
    location_label: Optional[str] = None
    storage_location_id: Optional[UUID] = None
    compatible_model_ids: list[UUID] = []


class ArticleUpdate(BaseModel):
    """Update article."""

    name: Optional[str] = Field(default=None, min_length=1, strip_whitespace=True)
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
    storage_location_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    compatible_model_ids: Optional[list[UUID]] = None


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
    storage_location_id: Optional[UUID] = None
    is_active: bool
    compatible_model_ids: list[UUID] = []
    created_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_models(cls, article: object) -> "ArticleRead":
        """Baut ArticleRead inkl. kompatibler Fahrzeugmodell-IDs auf."""
        obj = cls.model_validate(article)
        obj.compatible_model_ids = [m.id for m in getattr(article, "compatible_models", [])]
        return obj
