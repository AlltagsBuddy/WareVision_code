"""Workshop order and WorkshopOrderItem models."""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.vehicle import Vehicle
    from app.models.article import Article
    from app.models.appointment import Appointment
    from app.models.user import User
    from app.models.invoice import Invoice


class WorkshopOrder(BaseModel):
    """Workshop order."""

    __tablename__ = "workshop_orders"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id"),
        nullable=False,
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id"),
        nullable=False,
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id"),
        nullable=True,
    )
    order_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # new, planned, in_progress, completed, invoiced, cancelled
    complaint_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    mileage_at_checkin: Mapped[int | None] = mapped_column(Integer, nullable=True)
    operating_hours_at_checkin: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_work_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_work_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    customer = relationship("Customer", back_populates="workshop_orders")
    vehicle = relationship("Vehicle", back_populates="workshop_orders")
    items = relationship(
        "WorkshopOrderItem",
        back_populates="workshop_order",
        cascade="all, delete-orphan",
    )
    invoices = relationship("Invoice", back_populates="workshop_order")


class WorkshopOrderItem(BaseModel):
    """Workshop order item (labor, material, service)."""

    __tablename__ = "workshop_order_items"

    workshop_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workshop_orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # labor, material, service
    article_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("articles.id"),
        nullable=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=1, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=19.00, nullable=False)
    source: Mapped[str] = mapped_column(
        String(30), default="manual", nullable=False
    )  # manual, maintenance_plan, automatic

    workshop_order = relationship("WorkshopOrder", back_populates="items")
