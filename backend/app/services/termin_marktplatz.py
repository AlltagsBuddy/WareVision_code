"""Terminmarktplatz-Integration: Webhook-Verarbeitung und Import-Logik."""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.appointment import Appointment

logger = logging.getLogger(__name__)
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
    Unterstützt verschiedene Feldnamen (snake_case, camelCase, etc.).
    """
    def get(key: str, *alt_keys: str) -> Any:
        for k in [key, *alt_keys]:
            if k in data and data[k] is not None:
                return data[k]
        return None

    return {
        "external_booking_id": str(get("external_booking_id", "externalBookingId", "booking_id", "bookingId", "id", "uuid") or ""),
        "starts_at": get("starts_at", "startsAt", "start_time", "startTime", "start", "date_from", "dateFrom"),
        "ends_at": get("ends_at", "endsAt", "end_time", "endTime", "end", "date_to", "dateTo"),
        "customer_first_name": get("customer_first_name", "customerFirstName", "first_name", "firstName", "vorname"),
        "customer_last_name": get("customer_last_name", "customerLastName", "last_name", "lastName", "nachname"),
        "customer_email": get("customer_email", "customerEmail", "email"),
        "customer_phone": get("customer_phone", "customerPhone", "phone", "telefon"),
        "vehicle_license_plate": get("vehicle_license_plate", "vehicleLicensePlate", "license_plate", "licensePlate", "kennzeichen"),
        "vehicle_vin": get("vehicle_vin", "vehicleVin", "vin"),
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
    # Payload kann in "data" oder "booking" gewrappt sein
    raw = payload
    if isinstance(payload.get("data"), dict):
        raw = payload["data"]
    elif isinstance(payload.get("booking"), dict):
        raw = payload["booking"]

    logger.info("Terminmarktplatz webhook received: external_id=%s", raw.get("external_booking_id") or raw.get("booking_id") or raw.get("id"))

    data = _normalize_webhook_payload(raw)
    external_id = data["external_booking_id"]
    if not external_id:
        logger.warning("Terminmarktplatz webhook: external_booking_id fehlt, payload keys=%s", list(raw.keys()))
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
        from app.services.audit import log_audit
        log_audit(db, user_id=None, entity_type="appointment", entity_id=existing.id, action="webhook_termin_marktplatz_cancel", new_values={"external_booking_id": external_id})
        logger.info("Terminmarktplatz: Termin storniert external_id=%s", external_id)
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
        from app.services.audit import log_audit
        log_audit(db, user_id=None, entity_type="appointment", entity_id=existing.id, action="webhook_termin_marktplatz_update", new_values={"external_booking_id": external_id})
        logger.info("Terminmarktplatz: Termin aktualisiert external_id=%s", external_id)
        return existing

    # booking: Dublettenschutz
    if existing:
        return existing

    # Neuen Termin anlegen
    def parse_datetime(val: Any) -> datetime | None:
        if val is None:
            return None
        s = str(val).strip()
        if not s:
            return None
        s = s.replace("Z", "+00:00").replace("z", "+00:00")
        # Leerzeichen statt T (z.B. "2025-03-20 10:00:00")
        if " " in s and "T" not in s:
            s = s.replace(" ", "T", 1)
        try:
            return datetime.fromisoformat(s)
        except (ValueError, AttributeError, TypeError):
            return None

    starts_at = parse_datetime(data.get("starts_at"))
    ends_at = parse_datetime(data.get("ends_at"))
    if not starts_at or not ends_at:
        logger.warning("Terminmarktplatz webhook: Datumsparsing fehlgeschlagen starts_at=%s ends_at=%s", data.get("starts_at"), data.get("ends_at"))
        return None
    # Naive Datetimes als lokale Zeit (Europe/Berlin) interpretieren
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=timezone.utc)
    if ends_at.tzinfo is None:
        ends_at = ends_at.replace(tzinfo=timezone.utc)

    if starts_at >= ends_at:
        logger.warning("Terminmarktplatz webhook: ends_at muss nach starts_at liegen")
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
    from app.services.audit import log_audit
    log_audit(db, user_id=None, entity_type="appointment", entity_id=apt.id, action="webhook_termin_marktplatz_import", new_values={"external_booking_id": external_id, "title": apt.title})
    logger.info("Terminmarktplatz: Termin importiert external_id=%s id=%s", external_id, apt.id)
    return apt
