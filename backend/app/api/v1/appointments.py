"""Appointments API."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.appointment import Appointment
from app.models.user import User
from app.schemas.appointment import AppointmentCreate, AppointmentRead, AppointmentUpdate

router = APIRouter(prefix="/appointments", tags=["appointments"])


def _check_overlap(db: Session, starts_at: datetime, ends_at: datetime, exclude_id: UUID | None = None) -> bool:
    """Check if time slot overlaps with existing appointments (excluding cancelled)."""
    q = (
        db.query(Appointment)
        .filter(Appointment.status != "cancelled")
        .filter(
            (Appointment.starts_at < ends_at) & (Appointment.ends_at > starts_at)
        )
    )
    if exclude_id:
        q = q.filter(Appointment.id != exclude_id)
    return q.first() is not None


@router.get("", response_model=list[AppointmentRead])
def list_appointments(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    from_date: datetime | None = Query(None, description="Start of date range (ISO)"),
    to_date: datetime | None = Query(None, description="End of date range (ISO)"),
    customer_id: UUID | None = None,
    status_filter: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
) -> list[Appointment]:
    """List appointments, optionally filtered by date range."""
    query = db.query(Appointment)
    if from_date:
        query = query.filter(Appointment.ends_at >= from_date)
    if to_date:
        query = query.filter(Appointment.starts_at <= to_date)
    if customer_id:
        query = query.filter(Appointment.customer_id == customer_id)
    if status_filter:
        query = query.filter(Appointment.status == status_filter)
    return query.order_by(Appointment.starts_at.asc()).offset(skip).limit(limit).all()


@router.post("", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED)
def create_appointment(
    payload: AppointmentCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Appointment:
    """Create appointment. Checks for overlaps."""
    if payload.starts_at >= payload.ends_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ende muss nach Beginn liegen",
        )
    if _check_overlap(db, payload.starts_at, payload.ends_at):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Zeitslot überschneidet sich mit einem bestehenden Termin",
        )
    apt = Appointment(
        customer_id=payload.customer_id,
        vehicle_id=payload.vehicle_id,
        appointment_type=payload.appointment_type,
        source="internal",
        status="planned",
        title=payload.title,
        description=payload.description,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        created_by=current_user.id,
    )
    db.add(apt)
    db.commit()
    db.refresh(apt)
    return apt


@router.get("/{appointment_id}", response_model=AppointmentRead)
def get_appointment(
    appointment_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Appointment:
    """Get appointment by ID."""
    apt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not apt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Termin nicht gefunden",
        )
    return apt


@router.patch("/{appointment_id}", response_model=AppointmentRead)
def update_appointment(
    appointment_id: UUID,
    payload: AppointmentUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Appointment:
    """Update appointment. Checks overlap on time change."""
    apt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not apt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Termin nicht gefunden",
        )
    starts_at = payload.starts_at if payload.starts_at is not None else apt.starts_at
    ends_at = payload.ends_at if payload.ends_at is not None else apt.ends_at
    if starts_at >= ends_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ende muss nach Beginn liegen",
        )
    if _check_overlap(db, starts_at, ends_at, exclude_id=appointment_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Zeitslot überschneidet sich mit einem bestehenden Termin",
        )
    if payload.customer_id is not None:
        apt.customer_id = payload.customer_id
    if payload.vehicle_id is not None:
        apt.vehicle_id = payload.vehicle_id
    if payload.status is not None:
        apt.status = payload.status
    if payload.title is not None:
        apt.title = payload.title
    if payload.description is not None:
        apt.description = payload.description
    if payload.starts_at is not None:
        apt.starts_at = payload.starts_at
    if payload.ends_at is not None:
        apt.ends_at = payload.ends_at
    db.commit()
    db.refresh(apt)
    return apt


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appointment(
    appointment_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Delete (cancel) appointment."""
    apt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not apt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Termin nicht gefunden",
        )
    apt.status = "cancelled"
    db.commit()
