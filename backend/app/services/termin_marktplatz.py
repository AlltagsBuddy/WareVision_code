"""Terminmarktplatz-Integration: Webhook-Verarbeitung und Import-Logik."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.customer import Customer
from app.models.manufacturer import Manufacturer
from app.models.user import User
from app.models.vehicle import Vehicle


def _get_admin_user_id(db: Session) -> UUID | None:
    """Ersten Admin-User für created_by bei Webhook-Import."""
    from app.models.role import Role
    admin = db.query(User).join(Role, User.role_id == Role.id).filter(Role.name == "admin").first()
    return admin.id if admin else None


def _normalize_webhook_payload(data: dict[str, Any]) -> dict[str, Any]:
    """
    Normalisiert Webhook-Payload von Terminmarktplatz oder ähnlichen Systemen.
    Unterstützt verschiedene Feldnamen.
    """
    def get(key: str, *alt_keys: str) -> Any:
        for k in [key, *alt_keys]:
            if k in data and data[k] is not None:
                return data[k]
        return None

    return {
        "external_booking_id": str(get("external_booking_id", "booking_id", "id", "uuid") or ""),
        "starts_at": get("starts_at", "start_time", "start", "date_from"),
        "ends_at": get("ends_at", "end_time", "end", "date_to"),
        "customer_first_name": get("customer_first_name", "first_name", "vorname"),
        "customer_last_name": get("customer_last_name", "last_name", "nachname"),
        "customer_email": get("customer_email", "email"),
        "customer_phone": get("customer_phone", "phone", "telefon"),
        "vehicle_license_plate": get("vehicle_license_plate", "license_plate", "kennzeichen"),
        "vehicle_vin": get("vehicle_vin", "vin"),
        "title": get("title", "subject"),
        "description": get("description", "notes", "bemerkung"),
        "action": get("action", "event"),  # booking, cancel, update
    }


def process_webhook(db: Session, payload: dict[str, Any]) -> Appointment | None:
    """
    Verarbeitet Webhook von Terminmarktplatz.
    - action=booking oder fehlt: Termin anlegen oder bestehenden zurückgeben (Dublettenschutz)
    - action=cancel: Termin stornieren
    - action=update: Termin aktualisieren (falls unterstützt)
    """
    data = _normalize_webhook_payload(payload)
    external_id = data["external_booking_id"]
    if not external_id:
        return None

    existing = (
        db.query(Appointment)
        .filter(Appointment.external_booking_id == external_id)
        .first()
    )

    action = (data.get("action") or "booking").lower()

    if action == "cancel" and existing:
        existing.status = "cancelled"
        db.commit()
        db.refresh(existing)
        return existing

    if action == "update" and existing:
        if data.get("starts_at"):
            try:
                existing.starts_at = datetime.fromisoformat(
                    str(data["starts_at"]).replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass
        if data.get("ends_at"):
            try:
                existing.ends_at = datetime.fromisoformat(
                    str(data["ends_at"]).replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass
        db.commit()
        db.refresh(existing)
        return existing

    # booking: Dublettenschutz
    if existing:
        return existing

    # Neuen Termin anlegen
    try:
        starts_at = datetime.fromisoformat(
            str(data["starts_at"]).replace("Z", "+00:00")
        )
        ends_at = datetime.fromisoformat(
            str(data["ends_at"]).replace("Z", "+00:00")
        )
    except (ValueError, AttributeError, TypeError):
        return None

    if starts_at >= ends_at:
        return None

    customer_id = None
    if data.get("customer_email") or data.get("customer_first_name") or data.get("customer_last_name"):
        email = (data.get("customer_email") or "").strip().lower()
        customer = (
            db.query(Customer).filter(Customer.email == email).first()
            if email
            else None
        )
        if not customer:
            customer = Customer(
                customer_type="B2C",
                first_name=data.get("customer_first_name") or "",
                last_name=data.get("customer_last_name") or "",
                email=data.get("customer_email") or None,
                phone=data.get("customer_phone") or None,
            )
            db.add(customer)
            db.flush()
        customer_id = customer.id

    vehicle_id = None
    if customer_id and (data.get("vehicle_license_plate") or data.get("vehicle_vin")):
        manufacturer = db.query(Manufacturer).filter(Manufacturer.name == "Sonstige").first()
        if not manufacturer:
            manufacturer = Manufacturer(name="Sonstige")
            db.add(manufacturer)
            db.flush()

        vehicle = None
        if data.get("vehicle_license_plate"):
            vehicle = (
                db.query(Vehicle)
                .filter(
                    Vehicle.customer_id == customer_id,
                    Vehicle.license_plate == data["vehicle_license_plate"],
                )
                .first()
            )
        if not vehicle and data.get("vehicle_vin"):
            vehicle = (
                db.query(Vehicle)
                .filter(
                    Vehicle.customer_id == customer_id,
                    Vehicle.vin == data["vehicle_vin"],
                )
                .first()
            )
        if not vehicle:
            vehicle = Vehicle(
                customer_id=customer_id,
                manufacturer_id=manufacturer.id,
                category="motorcycle",
                license_plate=data.get("vehicle_license_plate"),
                vin=data.get("vehicle_vin"),
            )
            db.add(vehicle)
            db.flush()
        vehicle_id = vehicle.id

    admin_id = _get_admin_user_id(db)
    apt = Appointment(
        customer_id=customer_id,
        vehicle_id=vehicle_id,
        appointment_type="workshop",
        source="termin_marktplatz",
        external_booking_id=external_id,
        status="planned",
        title=data.get("title") or "Termin (Terminmarktplatz)",
        description=data.get("description"),
        starts_at=starts_at,
        ends_at=ends_at,
        created_by=admin_id,
    )
    db.add(apt)
    db.commit()
    db.refresh(apt)
    return apt
