"""Workshop orders API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.workshop_order import WorkshopOrder
from app.models.user import User
from app.schemas.workshop_order import WorkshopOrderCreate, WorkshopOrderRead

router = APIRouter(prefix="/workshop-orders", tags=["workshop-orders"])


def _next_order_number(db: Session) -> str:
    """Generate next order number (e.g. WO-2026-0001)."""
    from datetime import datetime
    year = datetime.now().year
    last = (
        db.query(WorkshopOrder)
        .filter(WorkshopOrder.order_number.like(f"WO-{year}-%"))
        .order_by(WorkshopOrder.order_number.desc())
        .first()
    )
    num = 1
    if last:
        try:
            num = int(last.order_number.split("-")[-1]) + 1
        except (IndexError, ValueError):
            pass
    return f"WO-{year}-{num:04d}"


@router.get("", response_model=list[WorkshopOrderRead])
def list_workshop_orders(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    customer_id: UUID | None = None,
    status_filter: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[WorkshopOrder]:
    """List workshop orders."""
    query = db.query(WorkshopOrder)
    if customer_id:
        query = query.filter(WorkshopOrder.customer_id == customer_id)
    if status_filter:
        query = query.filter(WorkshopOrder.status == status_filter)
    return query.order_by(WorkshopOrder.created_at.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=WorkshopOrderRead, status_code=status.HTTP_201_CREATED)
def create_workshop_order(
    payload: WorkshopOrderCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WorkshopOrder:
    """Create workshop order."""
    order_number = _next_order_number(db)
    order = WorkshopOrder(
        customer_id=payload.customer_id,
        vehicle_id=payload.vehicle_id,
        appointment_id=payload.appointment_id,
        order_number=order_number,
        status="new",
        complaint_description=payload.complaint_description,
        internal_notes=payload.internal_notes,
        mileage_at_checkin=payload.mileage_at_checkin,
        operating_hours_at_checkin=payload.operating_hours_at_checkin,
        estimated_work_minutes=payload.estimated_work_minutes,
        created_by=current_user.id,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.get("/{order_id}", response_model=WorkshopOrderRead)
def get_workshop_order(
    order_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WorkshopOrder:
    """Get workshop order by ID."""
    order = db.query(WorkshopOrder).filter(WorkshopOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Werkstattauftrag nicht gefunden",
        )
    return order
