"""Document schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class DocumentRead(BaseModel):
    """Document read."""

    id: UUID
    customer_id: Optional[UUID] = None
    vehicle_id: Optional[UUID] = None
    filename: str
    content_type: str
    file_size: int
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentAssign(BaseModel):
    """Assign document to customer/vehicle."""

    customer_id: Optional[UUID] = None
    vehicle_id: Optional[UUID] = None
