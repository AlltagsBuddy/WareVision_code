"""User schemas."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field

# Standardberechtigungen fuer neue Nicht-Admin-Benutzer
DEFAULT_PERMISSIONS: Dict[str, Any] = {
    "customers": {"visible": True, "write": True},
    "vehicles": {"visible": True, "write": True},
    "articles": {"visible": True, "write": True},
    "suppliers": {"visible": True, "write": True},
    "stock": {"visible": True, "write": True},
    "workshop_orders": {"visible": True, "write": True},
    "maintenance_plans": {"visible": True, "write": True},
    "appointments": {"visible": True, "write": True},
    "invoices": {"visible": True, "write": True},
    "documents": {"visible": True, "write": True},
}


class UserCreate(BaseModel):
    """Create user."""

    email: str
    first_name: str
    last_name: str
    password: str = Field(..., min_length=6)
    role_id: UUID
    permissions: Optional[Dict[str, Any]] = None


class UserUpdate(BaseModel):
    """Update user."""

    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6)
    permissions: Optional[Dict[str, Any]] = None


class UserRead(BaseModel):
    """User read (kein Passwort)."""

    id: UUID
    email: str
    first_name: str
    last_name: str
    role_id: UUID
    role_name: str
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    permissions: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
