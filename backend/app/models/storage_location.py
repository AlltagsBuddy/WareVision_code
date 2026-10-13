"""Lagerort-Modell."""

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class StorageLocation(BaseModel):
    """Lagerort – kann Artikeln und Fahrzeugen zugewiesen werden."""

    __tablename__ = "storage_locations"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
