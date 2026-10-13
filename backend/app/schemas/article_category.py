"""Article category schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ArticleCategoryCreate(BaseModel):
    """Neue Artikelkategorie anlegen."""

    name: str
    description: Optional[str] = None


class ArticleCategoryUpdate(BaseModel):
    """Artikelkategorie aktualisieren – alle Felder optional."""

    name: Optional[str] = None
    description: Optional[str] = None


class ArticleCategoryRead(BaseModel):
    """Artikelkategorie lesen."""

    id: UUID
    name: str
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
