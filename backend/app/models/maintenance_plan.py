"""Maintenance plan and task models."""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.manufacturer import Manufacturer, VehicleModel
    from app.models.article import Article


class MaintenancePlan(BaseModel):
    """Maintenance plan (e.g. by manufacturer/model)."""

    __tablename__ = "maintenance_plans"

    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("manufacturers.id", ondelete="CASCADE"),
        nullable=False,
    )
    vehicle_model_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_models.id", ondelete="CASCADE"),
        nullable=True,
    )
    # Optionales Hersteller-Dokument (PDF) das dem Plan beiliegt
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    interval_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    interval_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    interval_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Optionaler Baujahr-Bereich (z. B. eigener Plan für ältere Fahrzeuge); leer = alle Baujahre
    build_year_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    build_year_to: Mapped[int | None] = mapped_column(Integer, nullable=True)

    manufacturer = relationship("Manufacturer", back_populates="maintenance_plans")
    vehicle_model = relationship("VehicleModel", back_populates="maintenance_plans")
    document = relationship("Document", foreign_keys=[document_id])
    tasks = relationship(
        "MaintenanceTask",
        back_populates="maintenance_plan",
        cascade="all, delete-orphan",
    )


class MaintenanceTask(BaseModel):
    """Single task within a maintenance plan."""

    __tablename__ = "maintenance_tasks"

    maintenance_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maintenance_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Optionaler Artikel der automatisch in den Werkstattauftrag übernommen wird
    article_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="SET NULL"),
        nullable=True,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=1, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)

    maintenance_plan = relationship("MaintenancePlan", back_populates="tasks")
    article = relationship("Article")
