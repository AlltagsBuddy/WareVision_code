"""Manufacturer and VehicleModel models."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.vehicle import Vehicle


class Manufacturer(BaseModel):
    """Vehicle manufacturer (e.g. Yamaha, Honda)."""

    __tablename__ = "manufacturers"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    models = relationship("VehicleModel", back_populates="manufacturer", cascade="all, delete-orphan")
    vehicles = relationship("Vehicle", back_populates="manufacturer")


class VehicleModel(BaseModel):
    """Vehicle model (e.g. Grizzly 700)."""

    __tablename__ = "vehicle_models"

    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("manufacturers.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    variant: Mapped[str | None] = mapped_column(String(150), nullable=True)

    manufacturer = relationship("Manufacturer", back_populates="models")
    vehicles = relationship("Vehicle", back_populates="vehicle_model")
