"""Appointments API."""

import logging
from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, module_guard
from app.core.database import get_db
from app.models.appointment import Appointment
from app.models.app_setting import AppSetting
from app.models.customer import Customer
from app.models.manufacturer import Manufacturer
from app.models.vehicle import Vehicle
from app.models.user import User
from app.schemas.appointment import (
    AppointmentCancelResponse,
    AppointmentCreate,
    AppointmentRead,
    AppointmentUpdate,
    ExternalAppointmentImport,
)
from app.services.termin_marktplatz import resolve_appointment_type_for_terminmarktplatz

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/appointments", tags=["appointments"], dependencies=[Depends(module_guard("appointments"))])

_BERLIN_TZ = ZoneInfo("Europe/Berlin")


def _format_appointment_datetime(dt: datetime) -> str:
    """Terminzeit für E-Mails (deutsch, Europe/Berlin)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone(_BERLIN_TZ)
    return local.strftime("%d.%m.%Y, %H:%M Uhr")


def _company_name_from_settings(db: Session) -> str:
    row = db.query(AppSetting).filter(AppSetting.key == "company_name").first()
    return (row.value or "Quad Paradies Schoner").strip() if row else "Quad Paradies Schoner"


def _to_appointment_read(
    apt: Appointment,
    *,
    email_benachrichtigung: str | None = None,
) -> AppointmentRead:
    """Build AppointmentRead from Appointment (customer must be loaded for customer_* fields)."""
    return AppointmentRead(
        id=apt.id,
        customer_id=apt.customer_id,
        vehicle_id=apt.vehicle_id,
        appointment_type=apt.appointment_type,
        source=apt.source,
        status=apt.status,
        title=apt.title,
        description=apt.description,
        starts_at=apt.starts_at,
        ends_at=apt.ends_at,
        created_at=apt.created_at,
        customer_first_name=apt.customer.first_name if apt.customer else None,
        customer_last_name=apt.customer.last_name if apt.customer else None,
        customer_email=apt.customer.email if apt.customer else None,
        customer_phone=apt.customer.phone if apt.customer else None,
        email_benachrichtigung=email_benachrichtigung,
    )


def _check_overlap(
    db: Session,
    starts_at: datetime,
    ends_at: datetime,
    appointment_type: str = "workshop",
    exclude_id: UUID | None = None,
) -> bool:
    """Prüft ob Zeitslot mit bestehenden Terminen kollidiert (stornierte ausgeschlossen).
    Nur workshop-Termine blockieren einander – Probefahrten können parallel laufen."""
    if appointment_type != "workshop":
        # Probefahrten dürfen parallel stattfinden
        return False
    q = (
        db.query(Appointment)
        .filter(
            Appointment.status != "cancelled",
            Appointment.appointment_type == "workshop",
            Appointment.starts_at < ends_at,
            Appointment.ends_at > starts_at,
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
    search: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> list[Appointment]:
    """List appointments, optionally filtered by date range.
    search: Titel, Beschreibung, Kundenname/Firma oder Kennzeichen."""
    query = db.query(Appointment).options(joinedload(Appointment.customer))
    if search and search.strip():
        term = f"%{search.strip()}%"
        customer_ids = select(Customer.id).where(
            Customer.first_name.ilike(term) | Customer.last_name.ilike(term) | Customer.company_name.ilike(term)
            | func.concat(Customer.first_name, " ", Customer.last_name).ilike(term)
        )
        vehicle_ids = select(Vehicle.id).where(Vehicle.license_plate.ilike(term) | Vehicle.vin.ilike(term))
        query = query.filter(
            Appointment.title.ilike(term)
            | Appointment.description.ilike(term)
            | Appointment.customer_id.in_(customer_ids)
            | Appointment.vehicle_id.in_(vehicle_ids)
        )
    if from_date:
        query = query.filter(Appointment.ends_at >= from_date)
    if to_date:
        query = query.filter(Appointment.starts_at <= to_date)
    if customer_id:
        query = query.filter(Appointment.customer_id == customer_id)
    if status_filter:
        query = query.filter(Appointment.status == status_filter)
    appointments = query.order_by(Appointment.starts_at.asc()).offset(skip).limit(limit).all()
    return [_to_appointment_read(apt) for apt in appointments]


@router.post("", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED)
def create_appointment(
    payload: AppointmentCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AppointmentRead:
    """Create appointment. Checks for overlaps."""
    if payload.starts_at >= payload.ends_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ende muss nach Beginn liegen",
        )
    if _check_overlap(db, payload.starts_at, payload.ends_at, appointment_type=payload.appointment_type):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Zeitslot überschneidet sich mit einem bestehenden Werkstatt-Termin",
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

    mail_hinweis: str | None = None

    # Terminbestätigung per E-Mail (nur interne Termine, Kunde mit E-Mail)
    apt_with_customer = (
        db.query(Appointment)
        .options(joinedload(Appointment.customer))
        .filter(Appointment.id == apt.id)
        .first()
    )
    if not apt_with_customer:
        mail_hinweis = "Interner Fehler: Termin nach dem Speichern nicht gefunden."
    elif not apt_with_customer.customer_id:
        mail_hinweis = (
            "Keine Terminbestätigung: Es ist kein Kunde am Termin ausgewählt. "
            "Bitte Kunden in der Liste wählen (nicht „Optional“)."
        )
        logger.info(
            "Terminbestätigung übersprungen: kein customer_id (Termin %s)",
            apt.id,
        )
    elif not apt_with_customer.customer:
        mail_hinweis = "Keine Terminbestätigung: Kunde konnte nicht geladen werden."
        logger.warning("Termin %s: customer_id gesetzt, aber Customer fehlt in DB", apt.id)
    else:
        cust = apt_with_customer.customer
        to_mail = (cust.email or "").strip()
        if not to_mail:
            mail_hinweis = (
                "Keine Terminbestätigung: Beim gewählten Kunden ist keine E-Mail-Adresse hinterlegt."
            )
            logger.info(
                "Terminbestätigung übersprungen: Kunde ohne E-Mail (Termin %s, Kunde %s)",
                apt.id,
                cust.id,
            )
        else:
            try:
                from app.services.email import send_appointment_confirmation

                name_parts = [cust.first_name or "", cust.last_name or ""]
                customer_name = " ".join(p for p in name_parts if p).strip() or "Guten Tag"
                title = apt.title or "Termin"
                send_appointment_confirmation(
                    db,
                    to_email=to_mail,
                    customer_name=customer_name,
                    title=title,
                    starts_at=_format_appointment_datetime(apt.starts_at),
                    ends_at=_format_appointment_datetime(apt.ends_at),
                    company_name=_company_name_from_settings(db),
                )
                mail_hinweis = f"Terminbestätigung wurde an {to_mail} gesendet."
                logger.info(
                    "Terminbestätigung gesendet (Termin %s → %s)",
                    apt.id,
                    to_mail,
                )
            except Exception as e:
                msg = str(e).strip()
                if len(msg) > 280:
                    msg = msg[:280] + "…"
                mail_hinweis = (
                    f"Terminbestätigung konnte nicht gesendet werden: {msg}"
                )
                logger.exception(
                    "Terminbestätigung fehlgeschlagen (Termin %s, %s)",
                    apt.id,
                    to_mail,
                )

    out_apt = apt_with_customer if apt_with_customer else apt
    # Response mit Hinweis für die UI (nur bei diesem Endpoint ausgefüllt)
    return _to_appointment_read(out_apt, email_benachrichtigung=mail_hinweis)


@router.get("/webhook/termin-marktplatz/ping")
def termin_marktplatz_webhook_ping() -> dict:
    """
    Öffentlicher Ping – keine Auth. Prüft ob Anfragen WareVision erreichen.
    Gibt 200 zurück wenn der Server erreichbar ist.
    """
    return {"status": "ok", "message": "WareVision Webhook erreichbar"}


def _verify_termin_marktplatz_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    authorization: Annotated[str | None, Header()] = None,
    db: Annotated[Session, Depends(get_db)] = None,
) -> None:
    """Prüft API-Key für Terminmarktplatz-Webhook."""
    import logging
    log = logging.getLogger(__name__)
    stored = db.query(AppSetting).filter(AppSetting.key == "termin_marktplatz_api_key").first()
    expected = (stored.value or "").strip() if stored else ""
    if not expected:
        log.warning("Terminmarktplatz webhook: API-Schlüssel nicht konfiguriert")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Terminmarktplatz-Integration nicht konfiguriert. API-Schlüssel in Einstellungen hinterlegen.",
        )
    token = (x_api_key or "").strip()
    if not token and authorization and authorization.startswith("Bearer "):
        token = (authorization[7:] or "").strip()
    if not token or token != expected:
        log.warning("Terminmarktplatz webhook: API-Schlüssel ungültig (Header vorhanden: %s)", bool(x_api_key or authorization))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültiger API-Schlüssel",
        )


@router.get("/webhook/termin-marktplatz/health")
def termin_marktplatz_webhook_health(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[None, Depends(_verify_termin_marktplatz_api_key)],
) -> dict:
    """
    Prüft Verbindung und API-Schlüssel. GET mit Header X-API-Key.
    Gibt 200 zurück wenn der Schlüssel gültig ist.
    """
    return {"status": "ok", "message": "API-Schlüssel gültig, Webhook bereit"}


def _parse_termin_marktplatz_webhook_body(body: Any) -> dict[str, Any]:
    """
    Viele Anbieter senden JSON-Arrays statt Objekte ([{...}]) – FastAPI würde sonst 422 liefern.
    """
    if isinstance(body, dict):
        return body
    if isinstance(body, list):
        if not body:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Leeres JSON-Array: Buchungsobjekt erwartet.",
            )
        first = body[0]
        if not isinstance(first, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Erstes Array-Element muss ein JSON-Objekt sein.",
            )
        return first
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Body muss ein JSON-Objekt oder ein Array mit einem Objekt sein.",
    )


@router.post("/webhook/termin-marktplatz", response_model=AppointmentRead)
async def termin_marktplatz_webhook(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[None, Depends(_verify_termin_marktplatz_api_key)],
) -> AppointmentRead:
    """
    Webhook für Terminmarktplatz.de – automatischer Import gebuchter Termine.
    Kein Login erforderlich, Authentifizierung per X-API-Key oder Authorization: Bearer.
    Erwartetes JSON: external_booking_id, starts_at, ends_at (ISO), customer_*, vehicle_*, optional action (booking|cancel|update).
    """
    import logging

    log = logging.getLogger(__name__)
    try:
        body: Any = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültiges oder leeres JSON.",
        ) from None

    payload = _parse_termin_marktplatz_webhook_body(body)
    log.info("Terminmarktplatz webhook POST received, payload keys=%s", list(payload.keys()))

    from app.services.termin_marktplatz import _unwrap_webhook_payload, process_webhook
    from app.services.audit import log_audit

    result = process_webhook(db, payload)
    if result is None:
        raw = _unwrap_webhook_payload(payload)
        ext_id = (
            payload.get("external_booking_id")
            or payload.get("booking_id")
            or (raw.get("external_booking_id") or raw.get("booking_id") if isinstance(raw, dict) else None)
        )
        err_detail = {
            "error": "Ungültige oder unvollständige Buchungsdaten",
            "hint": "Pflichtfelder: external_booking_id, starts_at, ends_at (ISO 8601, z.B. 2025-03-20T10:00:00+01:00)",
            "payload_keys": list(payload.keys()),
            "data_keys": list(raw.keys()) if isinstance(raw, dict) else [],
            "received_starts_at": (payload.get("starts_at") or (raw.get("starts_at") if isinstance(raw, dict) else None)),
            "received_ends_at": (payload.get("ends_at") or (raw.get("ends_at") if isinstance(raw, dict) else None)),
        }
        log_audit(
            db,
            user_id=None,
            entity_type="appointment",
            entity_id=None,
            action="webhook_termin_marktplatz_error",
            new_values={
                "error": err_detail["error"],
                "external_booking_id": str(ext_id) if ext_id else None,
                "payload_keys": err_detail["payload_keys"],
                "data_keys": err_detail["data_keys"],
                "received_starts_at": err_detail["received_starts_at"],
                "received_ends_at": err_detail["received_ends_at"],
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_detail,
        )

    apt = (
        db.query(Appointment)
        .options(joinedload(Appointment.customer))
        .filter(Appointment.id == result.id)
        .first()
        or result
    )
    return _to_appointment_read(apt)


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
                phone=(payload.customer_phone or "").strip() or None,
            )
            db.add(customer)
            db.flush()
        else:
            phone_new = (payload.customer_phone or "").strip()
            if phone_new:
                customer.phone = phone_new
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

    at_in = (payload.appointment_type or "").strip()
    at_lower = at_in.lower()
    if at_lower in ("workshop", "test_drive"):
        apt_type = at_lower
    elif not at_in:
        apt_type = resolve_appointment_type_for_terminmarktplatz(
            {
                "appointment_type_raw": None,
                "title": payload.title,
                "description": payload.description,
            }
        )
    else:
        apt_type = resolve_appointment_type_for_terminmarktplatz(
            {
                "appointment_type_raw": at_in,
                "title": payload.title,
                "description": payload.description,
            }
        )

    apt = Appointment(
        customer_id=customer_id,
        vehicle_id=vehicle_id,
        appointment_type=apt_type,
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
) -> AppointmentRead:
    """Get appointment by ID."""
    apt = (
        db.query(Appointment)
        .options(joinedload(Appointment.customer))
        .filter(Appointment.id == appointment_id)
        .first()
    )
    if not apt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Termin nicht gefunden",
        )
    return _to_appointment_read(apt)


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
    apt_type = payload.appointment_type if payload.appointment_type is not None else apt.appointment_type
    if _check_overlap(db, starts_at, ends_at, appointment_type=apt_type, exclude_id=appointment_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Zeitslot überschneidet sich mit einem bestehenden Werkstatt-Termin",
        )
    if payload.customer_id is not None:
        apt.customer_id = payload.customer_id
    if payload.vehicle_id is not None:
        apt.vehicle_id = payload.vehicle_id
    if payload.appointment_type is not None:
        apt.appointment_type = payload.appointment_type
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
    apt = (
        db.query(Appointment)
        .options(joinedload(Appointment.customer))
        .filter(Appointment.id == apt.id)
        .first()
    )
    return _to_appointment_read(apt)


@router.delete("/{appointment_id}", response_model=AppointmentCancelResponse)
def delete_appointment(
    appointment_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    reason: str | None = Query(None, description="Stornierungsgrund (für Terminmarktplatz-Benachrichtigung)"),
) -> AppointmentCancelResponse:
    """Delete (cancel) appointment. Optional reason for Terminmarktplatz notifications."""
    apt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not apt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Termin nicht gefunden",
        )
    # Daten für ggf. E-Mail vor Statusänderung merken
    cancel_title = apt.title or "Termin"
    cancel_starts_at = apt.starts_at
    cancel_source = apt.source
    cancel_customer_id = apt.customer_id

    apt.status = "cancelled"
    db.commit()

    result = AppointmentCancelResponse()

    # Interne Termine: Stornierungsmail direkt per Resend/SMTP
    if cancel_source == "internal" and cancel_customer_id:
        cust = db.query(Customer).filter(Customer.id == cancel_customer_id).first()
        if cust and (cust.email or "").strip():
            try:
                from app.services.email import send_appointment_cancellation

                name_parts = [cust.first_name or "", cust.last_name or ""]
                customer_name = " ".join(p for p in name_parts if p).strip() or "Guten Tag"
                send_appointment_cancellation(
                    db,
                    to_email=cust.email.strip(),
                    customer_name=customer_name,
                    title=cancel_title,
                    starts_at=_format_appointment_datetime(cancel_starts_at),
                    reason=reason,
                    company_name=_company_name_from_settings(db),
                )
            except Exception:
                logger.exception(
                    "Stornierungsmail konnte nicht gesendet werden (Termin %s)",
                    appointment_id,
                )

    # Bei Terminmarktplatz-Terminen: Callback aufrufen, damit Kunde Stornierungsmail erhält
    if (
        apt.source == "termin_marktplatz"
        and apt.external_booking_id
    ):
        from app.models.app_setting import AppSetting
        from app.services.termin_marktplatz import notify_termin_marktplatz_cancel
        from app.services.audit import log_audit

        callback_row = db.query(AppSetting).filter(
            AppSetting.key == "termin_marktplatz_cancel_callback_url"
        ).first()
        api_key_row = db.query(AppSetting).filter(
            AppSetting.key == "termin_marktplatz_api_key"
        ).first()
        callback_url = (callback_row.value or "").strip() if callback_row else ""
        api_key = (api_key_row.value or "").strip() if api_key_row else ""
        cancel_reason = (reason or "").strip() or None

        if callback_url:
            ok, err_msg = notify_termin_marktplatz_cancel(
                callback_url=callback_url,
                external_booking_id=apt.external_booking_id,
                reason=cancel_reason,
                api_key=api_key or None,
            )
            result.termin_marktplatz_notified = ok
            result.termin_marktplatz_error = err_msg
            log_audit(
                db,
                user_id=current_user.id,
                entity_type="appointment",
                entity_id=apt.id,
                action="termin_marktplatz_cancel_notify",
                new_values={
                    "external_booking_id": apt.external_booking_id,
                    "success": ok,
                    "reason": cancel_reason,
                    "error": err_msg,
                },
            )
        else:
            result.termin_marktplatz_error = "Storno-Callback-URL nicht konfiguriert. Bitte in Einstellungen → Terminmarktplatz eintragen."
            log_audit(
                db,
                user_id=current_user.id,
                entity_type="appointment",
                entity_id=apt.id,
                action="termin_marktplatz_cancel_skip",
                new_values={
                    "external_booking_id": apt.external_booking_id,
                    "hint": "Storno-Callback-URL nicht konfiguriert",
                },
            )

    return result
