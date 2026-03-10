"""Customer schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class CustomerAddressCreate(BaseModel):
    """Create customer address."""

    address_type: str = Field(..., pattern="^(billing|shipping|main)$")
    street: str
    house_number: Optional[str] = None
    postal_code: str
    city: str
    country: str = "Deutschland"


class CustomerAddressRead(CustomerAddressCreate):
    """Customer address read."""

    id: UUID
    customer_id: UUID

    class Config:
        from_attributes = True


class CustomerCreate(BaseModel):
    """Create customer."""

    customer_type: str = Field(..., pattern="^(B2B|B2C)$")
    company_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    vat_id: Optional[str] = None
    notes: Optional[str] = None


class CustomerUpdate(BaseModel):
    """Update customer."""

    customer_type: Optional[str] = Field(None, pattern="^(B2B|B2C)$")
    company_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    vat_id: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class CustomerRead(BaseModel):
    """Customer read."""

    id: UUID
    customer_type: str
    company_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    vat_id: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
