"""Vehicle schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class VehicleCreate(BaseModel):
    """Create vehicle."""

    customer_id: UUID
    manufacturer_id: UUID
    vehicle_model_id: Optional[UUID] = None
    model_name_free: Optional[str] = None
    category: str = Field(..., pattern="^(quad|motorcycle)$")
    build_year: Optional[int] = None
    vin: Optional[str] = None
    license_plate: Optional[str] = None
    mileage: Optional[int] = None
    operating_hours: Optional[int] = None
    engine_variant: Optional[str] = None
    color: Optional[str] = None
    notes: Optional[str] = None


class VehicleUpdate(BaseModel):
    """Update vehicle."""

    manufacturer_id: Optional[UUID] = None
    vehicle_model_id: Optional[UUID] = None
    model_name_free: Optional[str] = None
    category: Optional[str] = Field(None, pattern="^(quad|motorcycle)$")
    build_year: Optional[int] = None
    vin: Optional[str] = None
    license_plate: Optional[str] = None
    mileage: Optional[int] = None
    operating_hours: Optional[int] = None
    engine_variant: Optional[str] = None
    color: Optional[str] = None
    notes: Optional[str] = None


class VehicleRead(BaseModel):
    """Vehicle read."""

    id: UUID
    customer_id: UUID
    manufacturer_id: UUID
    vehicle_model_id: Optional[UUID] = None
    model_name_free: Optional[str] = None
    category: str
    build_year: Optional[int] = None
    vin: Optional[str] = None
    license_plate: Optional[str] = None
    mileage: Optional[int] = None
    operating_hours: Optional[int] = None
    engine_variant: Optional[str] = None
    color: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
