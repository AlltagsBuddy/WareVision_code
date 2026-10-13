"""Stundenpreis-Schemas."""

from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class LaborRateCreate(BaseModel):
    """Stundenpreis anlegen."""

    name: str
    description: Optional[str] = None
    rate_per_hour: Decimal = Field(gt=0)
    is_default: bool = False


class LaborRateUpdate(BaseModel):
    """Stundenpreis aktualisieren."""

    name: Optional[str] = None
    description: Optional[str] = None
    rate_per_hour: Optional[Decimal] = Field(default=None, gt=0)
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class LaborRateRead(BaseModel):
    """Stundenpreis lesen."""

    id: UUID
    name: str
    description: Optional[str] = None
    rate_per_hour: Decimal
    is_default: bool
    is_active: bool

    class Config:
        from_attributes = True
