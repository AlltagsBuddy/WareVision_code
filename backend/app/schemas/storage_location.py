"""Lagerort-Schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class StorageLocationCreate(BaseModel):
    """Neuen Lagerort anlegen."""

    name: str = Field(..., min_length=1, strip_whitespace=True)
    description: Optional[str] = None


class StorageLocationUpdate(BaseModel):
    """Lagerort aktualisieren."""

    name: Optional[str] = Field(default=None, min_length=1, strip_whitespace=True)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class StorageLocationRead(BaseModel):
    """Lagerort-Antwort."""

    id: UUID
    name: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
