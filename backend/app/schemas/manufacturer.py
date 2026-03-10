"""Manufacturer and VehicleModel schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ManufacturerCreate(BaseModel):
    """Create manufacturer."""

    name: str


class ManufacturerRead(BaseModel):
    """Manufacturer read."""

    id: UUID
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


class VehicleModelCreate(BaseModel):
    """Create vehicle model."""

    manufacturer_id: UUID
    name: str
    variant: Optional[str] = None


class VehicleModelRead(BaseModel):
    """Vehicle model read."""

    id: UUID
    manufacturer_id: UUID
    name: str
    variant: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
