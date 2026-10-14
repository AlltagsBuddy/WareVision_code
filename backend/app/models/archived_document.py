"""Belegarchiv (GoBD): unveränderbare Originale ausgegebener Dokumente (Rechnungen, Mahnungen, Angebote …)."""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class ArchivedDocument(BaseModel):
    """Einmal gespeichertes Original. Wird nie überschrieben oder gelöscht; Prüfsumme sichert die Unveränderbarkeit."""

    __tablename__ = "archived_documents"
    __table_args__ = (UniqueConstraint("entity_type", "entity_id", "kind", name="uq_archived_documents_entity_kind"),)

    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)    # invoice | quote | purchase_order
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)           # pdf | zugferd | reminder_1 …
    document_number: Mapped[str] = mapped_column(String(100), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    backfilled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
