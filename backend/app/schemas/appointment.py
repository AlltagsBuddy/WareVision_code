"""Appointment schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AppointmentCreate(BaseModel):
    """Create appointment."""

    customer_id: Optional[UUID] = None
    vehicle_id: Optional[UUID] = None
    appointment_type: str = Field(..., pattern="^(workshop|test_drive)$")
    title: Optional[str] = None
    description: Optional[str] = None
    starts_at: datetime
    ends_at: datetime


class AppointmentUpdate(BaseModel):
    """Update appointment."""

    customer_id: Optional[UUID] = None
    vehicle_id: Optional[UUID] = None
    status: Optional[str] = Field(None, pattern="^(planned|confirmed|rescheduled|cancelled|completed)$")
    title: Optional[str] = None
    description: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class AppointmentRead(BaseModel):
    """Appointment read."""

    id: UUID
    customer_id: Optional[UUID] = None
    vehicle_id: Optional[UUID] = None
    appointment_type: str
    source: str
    status: str
    title: Optional[str] = None
    description: Optional[str] = None
    starts_at: datetime
    ends_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True
