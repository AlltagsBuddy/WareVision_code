"""Customer and CustomerAddress models."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.vehicle import Vehicle
    from app.models.appointment import Appointment
    from app.models.workshop_order import WorkshopOrder
    from app.models.invoice import Invoice
    from app.models.document import Document


class Customer(BaseModel):
    """Customer (B2B or B2C)."""

    __tablename__ = "customers"

    customer_type: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # B2B, B2C
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    vat_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    addresses = relationship("CustomerAddress", back_populates="customer", cascade="all, delete-orphan")
    vehicles = relationship("Vehicle", back_populates="customer", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="customer")
    workshop_orders = relationship("WorkshopOrder", back_populates="customer")
    invoices = relationship("Invoice", back_populates="customer")
    documents = relationship("Document", back_populates="customer")


class CustomerAddress(BaseModel):
    """Customer address (billing, shipping, main)."""

    __tablename__ = "customer_addresses"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    address_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # billing, shipping, main
    street: Mapped[str] = mapped_column(String(255), nullable=False)
    house_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(100), default="Deutschland", nullable=False)

    customer = relationship("Customer", back_populates="addresses")
