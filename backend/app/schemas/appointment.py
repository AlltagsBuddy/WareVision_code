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


class ExternalAppointmentImport(BaseModel):
    """Import appointment from external system (Termin-Marktplatz etc.)."""

    external_booking_id: str
    starts_at: str  # ISO datetime
    ends_at: str  # ISO datetime
    customer_first_name: str | None = None
    customer_last_name: str | None = None
    customer_email: str | None = None
    customer_phone: str | None = None
    vehicle_license_plate: str | None = None
    vehicle_vin: str | None = None
    title: str | None = None
    description: str | None = None


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
