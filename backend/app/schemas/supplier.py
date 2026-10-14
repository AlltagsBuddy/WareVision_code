"""Lieferanten-Schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class SupplierCreate(BaseModel):
    """Neuen Lieferanten anlegen."""

    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    contact_person: Optional[str] = None
    street: Optional[str] = None
    house_number: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = "Deutschland"
    customer_number: Optional[str] = None
    notes: Optional[str] = None


class SupplierUpdate(BaseModel):
    """Lieferanten aktualisieren – alle Felder optional."""

    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    contact_person: Optional[str] = None
    street: Optional[str] = None
    house_number: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    customer_number: Optional[str] = None
    notes: Optional[str] = None


class SupplierRead(BaseModel):
    """Lieferant lesen."""

    id: UUID
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    contact_person: Optional[str] = None
    street: Optional[str] = None
    house_number: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    customer_number: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
