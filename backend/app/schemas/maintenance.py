"""Maintenance plan schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class MaintenanceTaskCreate(BaseModel):
    """Create maintenance task."""

    name: str
    description: Optional[str] = None
    sort_order: int = 0


class MaintenanceTaskRead(BaseModel):
    """Maintenance task read."""

    id: UUID
    maintenance_plan_id: UUID
    name: str
    description: Optional[str] = None
    sort_order: int

    class Config:
        from_attributes = True


class MaintenancePlanCreate(BaseModel):
    """Create maintenance plan."""

    manufacturer_id: UUID
    vehicle_model_id: Optional[UUID] = None
    name: str
    description: Optional[str] = None
    interval_km: Optional[int] = None
    interval_hours: Optional[int] = None
    interval_months: Optional[int] = None


class MaintenancePlanRead(BaseModel):
    """Maintenance plan read."""

    id: UUID
    manufacturer_id: UUID
    vehicle_model_id: Optional[UUID] = None
    name: str
    description: Optional[str] = None
    interval_km: Optional[int] = None
    interval_hours: Optional[int] = None
    interval_months: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
