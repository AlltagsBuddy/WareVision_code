"""Appointment model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.vehicle import Vehicle
    from app.models.user import User


class Appointment(BaseModel):
    """Appointment (workshop, test drive)."""

    __tablename__ = "appointments"

    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id"),
        nullable=True,
    )
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id"),
        nullable=True,
    )
    appointment_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # workshop, test_drive
    source: Mapped[str] = mapped_column(
        String(50), default="internal", nullable=False
    )  # internal, termin_marktplatz
    external_booking_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # planned, confirmed, rescheduled, cancelled, completed
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    customer = relationship("Customer", back_populates="appointments")
    vehicle = relationship("Vehicle", back_populates="appointments")
