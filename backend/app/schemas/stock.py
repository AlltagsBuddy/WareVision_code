"""Stock movement schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class StockMovementCreate(BaseModel):
    """Create stock movement."""

    article_id: UUID
    movement_type: str = Field(
        ...,
        pattern="^(incoming|outgoing|correction|workshop_consumption|invoice_consumption)$",
    )
    quantity: int = Field(..., gt=0)
    reference_type: Optional[str] = None
    reference_id: Optional[UUID] = None
    notes: Optional[str] = None


class StockMovementRead(BaseModel):
    """Stock movement read."""

    id: UUID
    article_id: UUID
    movement_type: str
    quantity: int
    reference_type: Optional[str] = None
    reference_id: Optional[UUID] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
