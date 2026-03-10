"""Stock movement model."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.article import Article
    from app.models.user import User


class StockMovement(BaseModel):
    """Stock movement (incoming, outgoing, correction, workshop_consumption)."""

    __tablename__ = "stock_movements"

    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("articles.id"),
        nullable=False,
    )
    movement_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )  # incoming, outgoing, correction, workshop_consumption, invoice_consumption
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    article = relationship("Article", back_populates="stock_movements")
