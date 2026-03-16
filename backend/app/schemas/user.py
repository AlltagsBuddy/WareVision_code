"""User schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """Create user."""

    email: str
    first_name: str
    last_name: str
    password: str = Field(..., min_length=6)
    role_id: UUID


class UserUpdate(BaseModel):
    """Update user."""

    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6)


class UserRead(BaseModel):
    """User read (no password)."""

    id: UUID
    email: str
    first_name: str
    last_name: str
    role_id: UUID
    role_name: str
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
