"""User schemas."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field

class UserCreate(BaseModel):
    """Create user."""

    email: str
    first_name: str
    last_name: str
    password: str = Field(..., min_length=10)
    role_id: UUID
    permissions: Optional[Dict[str, Any]] = None


class UserUpdate(BaseModel):
    """Update user."""

    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=10)
    permissions: Optional[Dict[str, Any]] = None


class UserRead(BaseModel):
    """User read (kein Passwort)."""

    id: UUID
    email: str
    first_name: str
    last_name: str
    role_id: UUID
    role_name: str
    role_label: str = ""
    is_manager: bool = False
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    permissions: Optional[Dict[str, Any]] = None
    totp_enabled: bool = False

    class Config:
        from_attributes = True
