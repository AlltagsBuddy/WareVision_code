"""Angebote / Kostenvoranschläge API."""

import logging
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.article import Article
from app.models.customer import Customer
from app.models.quote import Quote, QuoteItem
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.workshop_order import WorkshopOrder, WorkshopOrderItem
from app.schemas.quote import QuoteConvertIn, QuoteIn, QuoteRead, QuoteSendEmailIn, QuoteStatusIn
from app.services.audit import log_audit
from app.services.stock_booking import book_workshop_material_out

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quotes", tags=["quotes"])

_CENT = Decimal("0.01")
DEFAULT_VALIDITY_DAYS = 30

# Erlaubte Statuswechsel: aktueller Status -> mögliche neue Status
_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"sent", "accepted", "rejected"},
    "sent": {"accepted", "rejected"},
    "accepted": {"rejected"},
    "rejected": {"accepted"},
    "converted": set(),
}

_TYPE_LABEL = {"offer": "Angebot", "estimate": "Kostenvoranschlag"}


def _next_quote_number(db: Session) -> str:
    """Nächste Angebotsnummer erzeugen (z. B. AN-2026-0001)."""
    year = date.today().year
    last = (
        db.query(Quote)
        .filter(Quote.quote_number.like(f"AN-{year}-%"))
        .order_by(Quote.quote_number.desc())
        .first()
    )
    num = 1
    if last:
        try:
            num = int(last.quote_number.split("-")[-1]) + 1
        except (IndexError, ValueError):
            pass
    return f"AN-{year}-{num:04d}"


def _get_quote(db: Session, quote_id: UUID) -> Quote:
    """Angebot laden oder 404."""
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Angebot nicht gefunden")
    return quote


def _validate_refs(db: Session, customer_id: UUID, vehicle_id: UUID | None) -> Customer:
    """Kunde und Fahrzeug prüfen (Fahrzeug muss zum Kunden gehören)."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kunde nicht gefunden")
    if vehicle_id:
        vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not vehicle:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fahrzeug nicht gefunden")
        if vehicle.customer_id != customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Das Fahrzeug gehört nicht zu diesem Kunden",
            )
    return customer


def _apply_payload(db: Session, quote: Quote, payload: QuoteIn) -> None:
    """Kopfdaten und Positionen aus der Eingabe übernehmen und Summen berechnen."""
    _validate_refs(db, payload.customer_id, payload.vehicle_id)
    quote.quote_type = payload.quote_type
    quote.customer_id = payload.customer_id
    quote.vehicle_id = payload.vehicle_id
    quote.quote_date = payload.quote_date
    if payload.valid_until:
        quote.valid_until = payload.valid_until
    elif payload.quote_type == "offer":
        quote.valid_until = payload.quote_date + timedelta(days=DEFAULT_VALIDITY_DAYS)
    else:
        quote.valid_until = None
    quote.subject = (payload.subject or "").strip() or None
    quote.notes = (payload.notes or "").strip() or None
    quote.internal_notes = (payload.internal_notes or "").strip() or None

    # Positionen vollständig ersetzen
    quote.items.clear()
    db.flush()
    bases: dict[Decimal, Decimal] = {}
    for pos, it in enumerate(payload.items, 1):
        if it.article_id and not db.query(Article.id).filter(Article.id == it.article_id).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Artikel in Position {pos} nicht gefunden")
        line_net = (it.quantity * it.unit_price).quantize(_CENT, rounding=ROUND_HALF_UP)
        rate = it.vat_rate.quantize(_CENT)
        quote.items.append(QuoteItem(
            position=pos,
            item_type=it.item_type,
            article_id=it.article_id,
            description=it.description,
            quantity=it.quantity,
            unit=(it.unit or "").strip() or None,
            unit_price=it.unit_price,
            vat_rate=rate,
            line_total_net=line_net,
        ))
        bases[rate] = bases.get(rate, Decimal("0")) + line_net

    # MwSt je Steuersatz kaufmännisch gerundet (gleiche Rechenweise wie bei Rechnungen)
    net = sum(bases.values(), Decimal("0"))
    vat = sum(((b * r / 100).quantize(_CENT, rounding=ROUND_HALF_UP) for r, b in bases.items()), Decimal("0"))
    quote.net_amount = net
    quote.vat_amount = vat
    quote.gross_amount = net + vat


@router.get("", response_model=list[QuoteRead])
def list_quotes(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    customer_id: UUID | None = None,
    status_filter: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> list[Quote]:
    """Angebote auflisten (neueste zuerst)."""
    q = db.query(Quote)
    if customer_id:
        q = q.filter(Quote.customer_id == customer_id)
    if status_filter:
        q = q.filter(Quote.status == status_filter)
    return q.order_by(Quote.quote_date.desc(), Quote.quote_number.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=QuoteRead, status_code=status.HTTP_201_CREATED)
def create_quote(
    payload: QuoteIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Quote:
    """Neues Angebot / neuen Kostenvoranschlag als Entwurf anlegen."""
    quote = Quote(quote_number=_next_quote_number(db), status="draft", created_by=current_user.id)
    db.add(quote)
    _apply_payload(db, quote, payload)
    db.flush()
    log_audit(
        db, user_id=current_user.id, entity_type="quote", entity_id=quote.id, action="create",
        new_values={"quote_number": quote.quote_number, "gross_amount": str(quote.gross_amount)},
    )
    db.commit()
    db.refresh(quote)
    return quote


@router.get("/{quote_id}", response_model=QuoteRead)
def get_quote(
    quote_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Quote:
    """Einzelnes Angebot mit Positionen."""
    return _get_quote(db, quote_id)


@router.put("/{quote_id}", response_model=QuoteRead)
def update_quote(
    quote_id: UUID,
    payload: QuoteIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Quote:
    """Angebot bearbeiten – nur im Entwurf. Verschickte Angebote bitte als neue Version kopieren."""
    quote = _get_quote(db, quote_id)
    if quote.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur Entwürfe können bearbeitet werden. Bitte „Neue Version“ verwenden.",
        )
    old = {"gross_amount": str(quote.gross_amount)}
    _apply_payload(db, quote, payload)
    log_audit(
        db, user_id=current_user.id, entity_type="quote", entity_id=quote.id, action="update",
        old_values=old, new_values={"gross_amount": str(quote.gross_amount)},
    )
    db.commit()
    db.refresh(quote)
    return quote


@router.delete("/{quote_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quote(
    quote_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Angebot löschen – nur Entwürfe (verschickte Angebote bleiben nachvollziehbar)."""
    quote = _get_quote(db, quote_id)
    if quote.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur Entwürfe können gelöscht werden. Verschickte Angebote bitte auf „Abgelehnt“ setzen.",
        )
    log_audit(
        db, user_id=current_user.id, entity_type="quote", entity_id=quote.id, action="delete",
        old_values={"quote_number": quote.quote_number},
    )
    db.delete(quote)
    db.commit()


@router.post("/{quote_id}/status", response_model=QuoteRead)
def change_quote_status(
    quote_id: UUID,
    payload: QuoteStatusIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Quote:
    """Status ändern: versendet, angenommen, abgelehnt."""
    quote = _get_quote(db, quote_id)
    if payload.status not in _TRANSITIONS.get(quote.status, set()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Statuswechsel von „{quote.status}“ nach „{payload.status}“ ist nicht möglich",
        )
    old_status = quote.status
    quote.status = payload.status
    log_audit(
        db, user_id=current_user.id, entity_type="quote", entity_id=quote.id, action="status",
        old_values={"status": old_status}, new_values={"status": payload.status},
    )
    db.commit()
    db.refresh(quote)
    return quote


@router.post("/{quote_id}/duplicate", response_model=QuoteRead, status_code=status.HTTP_201_CREATED)
def duplicate_quote(
    quote_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Quote:
    """Neue Version: Kopie als Entwurf mit neuer Nummer und heutigem Datum."""
    src = _get_quote(db, quote_id)
    today = date.today()
    validity = (src.valid_until - src.quote_date) if src.valid_until else None
    copy = Quote(
        quote_number=_next_quote_number(db),
        quote_type=src.quote_type,
        status="draft",
        customer_id=src.customer_id,
        vehicle_id=src.vehicle_id,
        quote_date=today,
        valid_until=(today + validity) if validity is not None else None,
        subject=src.subject,
        notes=src.notes,
        internal_notes=src.internal_notes,
        net_amount=src.net_amount,
        vat_amount=src.vat_amount,
        gross_amount=src.gross_amount,
        previous_quote_id=src.id,
        created_by=current_user.id,
    )
    for it in src.items:
        copy.items.append(QuoteItem(
            position=it.position, item_type=it.item_type, article_id=it.article_id,
            description=it.description, quantity=it.quantity, unit=it.unit,
            unit_price=it.unit_price, vat_rate=it.vat_rate, line_total_net=it.line_total_net,
        ))
    db.add(copy)
    db.flush()
    log_audit(
        db, user_id=current_user.id, entity_type="quote", entity_id=copy.id, action="duplicate",
        new_values={"quote_number": copy.quote_number, "from": src.quote_number},
    )
    db.commit()
    db.refresh(copy)
    return copy


@router.post("/{quote_id}/convert", response_model=QuoteRead)
def convert_to_workshop_order(
    quote_id: UUID,
    payload: QuoteConvertIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Quote:
    """Angenommenes Angebot in einen Werkstattauftrag umwandeln (Positionen werden übernommen)."""
    from app.api.v1.workshop_orders import _next_order_number

    quote = _get_quote(db, quote_id)
    if quote.status == "converted":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Angebot wurde bereits umgewandelt")
    if quote.status not in ("draft", "sent", "accepted"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Abgelehnte Angebote können nicht umgewandelt werden",
        )
    vehicle_id = payload.vehicle_id or quote.vehicle_id
    if not vehicle_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Für einen Werkstattauftrag wird ein Fahrzeug benötigt. Bitte Fahrzeug auswählen.",
        )
    _validate_refs(db, quote.customer_id, vehicle_id)

    label = _TYPE_LABEL.get(quote.quote_type, "Angebot")
    complaint = (payload.complaint_description or "").strip() or quote.subject
    order = WorkshopOrder(
        customer_id=quote.customer_id,
        vehicle_id=vehicle_id,
        order_number=_next_order_number(db),
        status="new",
        complaint_description=complaint,
        internal_notes=f"Aus {label} {quote.quote_number}"
        + (f"\n{quote.internal_notes}" if quote.internal_notes else ""),
        created_by=current_user.id,
    )
    db.add(order)
    db.flush()

    try:
        for it in quote.items:
            wo_item = WorkshopOrderItem(
                workshop_order_id=order.id,
                item_type=it.item_type,
                article_id=it.article_id,
                description=it.description,
                quantity=it.quantity,
                unit=it.unit,
                unit_price=it.unit_price,
                vat_rate=it.vat_rate,
                source="manual",
            )
            db.add(wo_item)
            db.flush()
            # Material wie beim manuellen Hinzufügen aus dem Lager buchen
            book_workshop_material_out(db, wo_item, current_user.id)
    except HTTPException:
        db.rollback()
        raise

    quote.status = "converted"
    quote.workshop_order_id = order.id
    if not quote.vehicle_id:
        quote.vehicle_id = vehicle_id
    log_audit(
        db, user_id=current_user.id, entity_type="quote", entity_id=quote.id, action="convert",
        new_values={"workshop_order_number": order.order_number},
    )
    db.commit()
    db.refresh(quote)
    return quote


@router.get("/{quote_id}/pdf")
def get_quote_pdf(
    quote_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Angebot / Kostenvoranschlag als PDF."""
    from app.services.quote_pdf import generate_quote_pdf

    quote = _get_quote(db, quote_id)
    pdf_bytes = generate_quote_pdf(db, quote)
    label = _TYPE_LABEL.get(quote.quote_type, "Angebot")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{label}_{quote.quote_number}.pdf"'},
    )


@router.post("/{quote_id}/send-email", response_model=QuoteRead)
def send_quote_email(
    quote_id: UUID,
    payload: QuoteSendEmailIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Quote:
    """Angebot per E-Mail an den Kunden senden. Ein Entwurf wird dabei auf „versendet“ gesetzt."""
    from app.models.app_setting import AppSetting
    from app.services.email import send_email_with_attachment
    from app.services.quote_pdf import generate_quote_pdf

    quote = _get_quote(db, quote_id)
    if quote.status in ("rejected", "converted"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dieses Angebot kann nicht mehr versendet werden")
    recipient = (payload.recipient_email or "").strip() or (quote.customer.email or "").strip()
    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Keine E-Mail-Adresse. Bitte Empfänger angeben oder beim Kunden hinterlegen.",
        )

    row = db.query(AppSetting).filter(AppSetting.key == "company_name").first()
    company_name = ((row.value if row else "") or "WareVision").strip()
    label = _TYPE_LABEL.get(quote.quote_type, "Angebot")
    pdf_bytes = generate_quote_pdf(db, quote)
    body = (
        "Sehr geehrte Damen und Herren,\n\n"
        f"anbei erhalten Sie unser {label} {quote.quote_number}"
        + (f" ({quote.subject})" if quote.subject else "")
        + ".\n\nBei Fragen melden Sie sich gerne.\n\n"
        f"Mit freundlichen Grüßen\n{company_name}\n"
    )
    try:
        send_email_with_attachment(
            db,
            to_email=recipient,
            subject=f"{label} {quote.quote_number} – {company_name}",
            body=body,
            attachment_filename=f"{label}_{quote.quote_number}.pdf",
            attachment_data=pdf_bytes,
            attachment_content_type="application/pdf",
        )
    except Exception as exc:
        logger.exception("E-Mail-Versand fehlgeschlagen für Angebot %s", quote_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"E-Mail konnte nicht gesendet werden: {exc}",
        ) from exc

    if quote.status == "draft":
        quote.status = "sent"
    log_audit(
        db, user_id=current_user.id, entity_type="quote", entity_id=quote.id, action="email_sent",
        new_values={"recipient": recipient},
    )
    db.commit()
    db.refresh(quote)
    return quote
