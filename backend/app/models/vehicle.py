"""Vehicle model."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.manufacturer import Manufacturer
    from app.models.vehicle_model import VehicleModel
    from app.models.workshop_order import WorkshopOrder
    from app.models.appointment import Appointment


class Vehicle(BaseModel):
    """Vehicle (Quad, Motorrad) belonging to a customer."""

    __tablename__ = "vehicles"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id"),
        nullable=False,
    )
    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("manufacturers.id"),
        nullable=False,
    )
    vehicle_model_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_models.id"),
        nullable=True,
    )
    model_name_free: Mapped[str | None] = mapped_column(String(150), nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # quad, motorcycle
    build_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vin: Mapped[str | None] = mapped_column(String(100), nullable=True)
    license_plate: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mileage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    operating_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    engine_variant: Mapped[str | None] = mapped_column(String(100), nullable=True)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    customer = relationship("Customer", back_populates="vehicles")
    manufacturer = relationship("Manufacturer", back_populates="vehicles")
    vehicle_model = relationship("VehicleModel", back_populates="vehicles")
    workshop_orders = relationship("WorkshopOrder", back_populates="vehicle")
    appointments = relationship("Appointment", back_populates="vehicle")
