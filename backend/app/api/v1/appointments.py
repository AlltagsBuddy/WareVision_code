"""Appointments API."""

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.appointment import Appointment
from app.models.app_setting import AppSetting
from app.schemas.appointment import AppointmentRead
from app.models.customer import Customer
from app.models.manufacturer import Manufacturer
from app.models.vehicle import Vehicle
from app.models.user import User
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentRead,
    AppointmentUpdate,
    ExternalAppointmentImport,
)

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


def _verify_termin_marktplatz_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    authorization: Annotated[str | None, Header()] = None,
    db: Annotated[Session, Depends(get_db)] = None,
) -> None:
    """Prüft API-Key für Terminmarktplatz-Webhook."""
    stored = db.query(AppSetting).filter(AppSetting.key == "termin_marktplatz_api_key").first()
    expected = (stored.value or "").strip() if stored else ""
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Terminmarktplatz-Integration nicht konfiguriert. API-Schlüssel in Einstellungen hinterlegen.",
        )
    token = x_api_key
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    if not token or token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültiger API-Schlüssel",
        )


@router.post("/webhook/termin-marktplatz", response_model=AppointmentRead)
def termin_marktplatz_webhook(
    payload: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[None, Depends(_verify_termin_marktplatz_api_key)],
) -> Appointment | dict:
    """
    Webhook für Terminmarktplatz.de – automatischer Import gebuchter Termine.
    Kein Login erforderlich, Authentifizierung per X-API-Key oder Authorization: Bearer.
    Erwartetes JSON: external_booking_id, starts_at, ends_at (ISO), customer_*, vehicle_*, optional action (booking|cancel|update).
    """
    from app.services.termin_marktplatz import process_webhook

    result = process_webhook(db, payload)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültige oder unvollständige Buchungsdaten",
        )
    return result


@router.post("/import-external", response_model=AppointmentRead)
def import_external_appointment(
    payload: ExternalAppointmentImport,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Appointment:
    """
    Import appointment from external system (Termin-Marktplatz etc.).
    Dublettenschutz: Bei gleicher external_booking_id wird der bestehende Termin zurückgegeben.
    """
    existing = (
        db.query(Appointment)
        .filter(Appointment.external_booking_id == payload.external_booking_id)
        .first()
    )
    if existing:
        return existing

    try:
        starts_at = datetime.fromisoformat(payload.starts_at.replace("Z", "+00:00"))
        ends_at = datetime.fromisoformat(payload.ends_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültiges Datumsformat (ISO 8601 erwartet)",
        )
    if starts_at >= ends_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ende muss nach Beginn liegen",
        )

    customer_id = None
    if payload.customer_email or payload.customer_first_name or payload.customer_last_name:
        email = (payload.customer_email or "").strip().lower()
        customer = (
            db.query(Customer).filter(Customer.email == email).first()
            if email
            else None
        )
        if not customer:
            customer = Customer(
                customer_type="B2C",
                first_name=payload.customer_first_name or "",
                last_name=payload.customer_last_name or "",
                email=payload.customer_email or None,
                phone=payload.customer_phone or None,
            )
            db.add(customer)
            db.flush()
        customer_id = customer.id

    vehicle_id = None
    if customer_id and (payload.vehicle_license_plate or payload.vehicle_vin):
        manufacturer = db.query(Manufacturer).filter(Manufacturer.name == "Sonstige").first()
        if not manufacturer:
            manufacturer = Manufacturer(name="Sonstige")
            db.add(manufacturer)
            db.flush()

        vehicle = None
        if payload.vehicle_license_plate:
            vehicle = (
                db.query(Vehicle)
                .filter(
                    Vehicle.customer_id == customer_id,
                    Vehicle.license_plate == payload.vehicle_license_plate,
                )
                .first()
            )
        if not vehicle and payload.vehicle_vin:
            vehicle = (
                db.query(Vehicle)
                .filter(
                    Vehicle.customer_id == customer_id,
                    Vehicle.vin == payload.vehicle_vin,
                )
                .first()
            )
        if not vehicle:
            vehicle = Vehicle(
                customer_id=customer_id,
                manufacturer_id=manufacturer.id,
                category="motorcycle",
                license_plate=payload.vehicle_license_plate,
                vin=payload.vehicle_vin,
            )
            db.add(vehicle)
            db.flush()
        vehicle_id = vehicle.id

    apt = Appointment(
        customer_id=customer_id,
        vehicle_id=vehicle_id,
        appointment_type="workshop",
        source="termin_marktplatz",
        external_booking_id=payload.external_booking_id,
        status="planned",
        title=payload.title or "Termin (extern importiert)",
        description=payload.description,
        starts_at=starts_at,
        ends_at=ends_at,
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
