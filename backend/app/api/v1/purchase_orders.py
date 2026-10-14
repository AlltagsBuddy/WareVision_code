"""Bestellwesen API: Bestellvorschlag, Bestellungen beim Lieferanten, Versand und Wareneingang."""

import logging
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.article import Article
from app.models.purchase_order import OPEN_STATUSES, PurchaseOrder, PurchaseOrderItem
from app.models.stock_reservation import StockReservation
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.purchase_order import (
    PurchaseOrderIn,
    PurchaseOrderRead,
    PurchaseOrderReceiveIn,
    PurchaseOrderSendEmailIn,
    SuggestionGroup,
    SuggestionItem,
)
from app.services import archive
from app.services.audit import log_audit
from app.services.stock_booking import apply_stock_change

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/purchase-orders", tags=["purchase-orders"])

_CENT = Decimal("0.01")
NO_SUPPLIER_LABEL = "Ohne Lieferant"


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _next_order_number(db: Session) -> str:
    """Nächste Bestellnummer erzeugen (z. B. BE-2026-0001)."""
    year = date.today().year
    last = (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.order_number.like(f"BE-{year}-%"))
        .order_by(PurchaseOrder.order_number.desc())
        .first()
    )
    num = 1
    if last:
        try:
            num = int(last.order_number.split("-")[-1]) + 1
        except (IndexError, ValueError):
            pass
    return f"BE-{year}-{num:04d}"


def _get_order(db: Session, order_id: UUID) -> PurchaseOrder:
    """Bestellung laden oder 404."""
    order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bestellung nicht gefunden")
    return order


def _get_supplier(db: Session, supplier_id: UUID) -> Supplier:
    """Lieferant laden oder 400."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lieferant nicht gefunden")
    return supplier


def _apply_payload(db: Session, order: PurchaseOrder, payload: PurchaseOrderIn) -> None:
    """Kopfdaten und Positionen übernehmen, Summen berechnen (MwSt je Steuersatz gerundet)."""
    _get_supplier(db, payload.supplier_id)
    order.supplier_id = payload.supplier_id
    order.order_date = payload.order_date
    order.expected_date = payload.expected_date
    order.notes = (payload.notes or "").strip() or None
    order.internal_notes = (payload.internal_notes or "").strip() or None

    order.items.clear()
    bases: dict[Decimal, Decimal] = {}
    for pos, it in enumerate(payload.items, 1):
        article = None
        if it.article_id:
            article = db.query(Article).filter(Article.id == it.article_id).first()
            if not article:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Artikel in Position {pos} nicht gefunden")
        supplier_no = (it.supplier_article_number or "").strip() or (article.supplier_article_number if article else None)
        line_net = (Decimal(it.quantity) * it.unit_price).quantize(_CENT, rounding=ROUND_HALF_UP)
        rate = it.vat_rate.quantize(_CENT)
        order.items.append(PurchaseOrderItem(
            position=pos,
            article_id=it.article_id,
            description=it.description,
            article_number=article.article_number if article else None,
            supplier_article_number=supplier_no or None,
            quantity=it.quantity,
            received_quantity=0,
            unit=(it.unit or "").strip() or None,
            unit_price=it.unit_price,
            vat_rate=rate,
            line_total_net=line_net,
        ))
        bases[rate] = bases.get(rate, Decimal("0")) + line_net

    net = sum(bases.values(), Decimal("0"))
    vat = sum(((b * r / 100).quantize(_CENT, rounding=ROUND_HALF_UP) for r, b in bases.items()), Decimal("0"))
    order.net_amount = net
    order.vat_amount = vat
    order.gross_amount = net + vat


def _on_order_by_article(db: Session) -> dict[UUID, int]:
    """Bestellte, noch nicht gelieferte Mengen je Artikel (offene Bestellungen inkl. Entwürfe)."""
    rows = (
        db.query(
            PurchaseOrderItem.article_id,
            func.sum(PurchaseOrderItem.quantity - PurchaseOrderItem.received_quantity),
        )
        .join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderItem.purchase_order_id)
        .filter(PurchaseOrder.status.in_(OPEN_STATUSES), PurchaseOrderItem.article_id.isnot(None))
        .group_by(PurchaseOrderItem.article_id)
        .all()
    )
    return {aid: max(int(qty or 0), 0) for aid, qty in rows}


def _reserved_by_article(db: Session) -> dict[UUID, int]:
    """Aktive Reservierungen je Artikel (diese Teile gehen demnächst aus dem Lager)."""
    rows = (
        db.query(StockReservation.article_id, func.sum(StockReservation.quantity))
        .filter(StockReservation.status == "active")
        .group_by(StockReservation.article_id)
        .all()
    )
    return {aid: int(qty or 0) for aid, qty in rows}


def _check_editable(order: PurchaseOrder) -> None:
    """Nur Entwürfe dürfen geändert oder gelöscht werden."""
    if order.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur Entwürfe können geändert werden. Bestellte Bestellungen bitte stornieren und neu anlegen.",
        )


# ---------------------------------------------------------------------------
# Endpunkte
# ---------------------------------------------------------------------------

@router.get("", response_model=list[PurchaseOrderRead])
def list_purchase_orders(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    supplier_id: UUID | None = None,
    status_filter: str | None = None,
    open_only: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
) -> list[PurchaseOrder]:
    """Bestellungen auflisten (neueste zuerst)."""
    q = db.query(PurchaseOrder)
    if supplier_id:
        q = q.filter(PurchaseOrder.supplier_id == supplier_id)
    if status_filter:
        q = q.filter(PurchaseOrder.status == status_filter)
    if open_only:
        q = q.filter(PurchaseOrder.status.in_(OPEN_STATUSES))
    return q.order_by(PurchaseOrder.order_date.desc(), PurchaseOrder.order_number.desc()).offset(skip).limit(limit).all()


@router.get("/suggestions", response_model=list[SuggestionGroup])
def get_suggestions(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[SuggestionGroup]:
    """Bestellvorschlag: Artikel, deren verfügbarer Bestand unter dem Mindestbestand liegt.

    Verfügbar = Lagerbestand − aktive Reservierungen + bereits bestellte (offene) Menge.
    Vorgeschlagen wird die Menge bis zum Zielbestand (ohne Zielbestand: bis zum Mindestbestand).
    """
    on_order = _on_order_by_article(db)
    reserved = _reserved_by_article(db)
    articles = (
        db.query(Article)
        .filter(Article.is_active.is_(True), Article.minimum_stock > 0)
        .order_by(Article.article_number)
        .all()
    )
    groups: dict[UUID | None, SuggestionGroup] = {}
    for a in articles:
        ordered = on_order.get(a.id, 0)
        res = reserved.get(a.id, 0)
        available = a.stock_quantity - res + ordered
        if available >= a.minimum_stock:
            continue
        target = max(a.target_stock or 0, a.minimum_stock)
        qty = target - available
        if qty <= 0:
            continue
        key = a.supplier_id
        if key not in groups:
            sup = db.query(Supplier).filter(Supplier.id == key).first() if key else None
            groups[key] = SuggestionGroup(
                supplier_id=key,
                supplier_name=sup.name if sup else NO_SUPPLIER_LABEL,
                supplier_email=sup.email if sup else None,
                items=[],
            )
        groups[key].items.append(SuggestionItem(
            article_id=a.id,
            article_number=a.article_number,
            name=a.name,
            supplier_article_number=a.supplier_article_number,
            stock_quantity=a.stock_quantity,
            reserved_quantity=res,
            on_order_quantity=ordered,
            minimum_stock=a.minimum_stock,
            target_stock=a.target_stock,
            suggested_quantity=qty,
            unit_price=a.purchase_price or Decimal("0"),
            vat_rate=a.vat_rate,
        ))
    # Lieferanten alphabetisch, „Ohne Lieferant“ zuletzt
    return sorted(groups.values(), key=lambda g: (g.supplier_id is None, g.supplier_name.lower()))


@router.post("", response_model=PurchaseOrderRead, status_code=status.HTTP_201_CREATED)
def create_purchase_order(
    payload: PurchaseOrderIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PurchaseOrder:
    """Neue Bestellung als Entwurf anlegen."""
    order = PurchaseOrder(order_number=_next_order_number(db), status="draft", created_by=current_user.id)
    _apply_payload(db, order, payload)
    db.add(order)
    db.flush()
    log_audit(
        db, user_id=current_user.id, entity_type="purchase_order", entity_id=order.id, action="create",
        new_values={"order_number": order.order_number, "net_amount": str(order.net_amount)},
    )
    db.commit()
    db.refresh(order)
    return order


@router.get("/{order_id}", response_model=PurchaseOrderRead)
def get_purchase_order(
    order_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PurchaseOrder:
    """Einzelne Bestellung mit Positionen."""
    return _get_order(db, order_id)


@router.put("/{order_id}", response_model=PurchaseOrderRead)
def update_purchase_order(
    order_id: UUID,
    payload: PurchaseOrderIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PurchaseOrder:
    """Bestellung bearbeiten – nur im Entwurf."""
    order = _get_order(db, order_id)
    _check_editable(order)
    old = {"net_amount": str(order.net_amount)}
    _apply_payload(db, order, payload)
    log_audit(
        db, user_id=current_user.id, entity_type="purchase_order", entity_id=order.id, action="update",
        old_values=old, new_values={"net_amount": str(order.net_amount)},
    )
    db.commit()
    db.refresh(order)
    return order


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_purchase_order(
    order_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Entwurf löschen (bestellte Bestellungen bleiben nachvollziehbar und werden storniert)."""
    order = _get_order(db, order_id)
    _check_editable(order)
    log_audit(
        db, user_id=current_user.id, entity_type="purchase_order", entity_id=order.id, action="delete",
        old_values={"order_number": order.order_number},
    )
    db.delete(order)
    db.commit()


@router.post("/{order_id}/mark-sent", response_model=PurchaseOrderRead)
def mark_purchase_order_sent(
    order_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> PurchaseOrder:
    """Als bestellt markieren (z. B. telefonisch oder im Online-Shop bestellt)."""
    order = _get_order(db, order_id)
    if order.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Die Bestellung wurde bereits bestellt")
    order.status = "sent"
    order.sent_at = datetime.now(timezone.utc)
    log_audit(
        db, user_id=current_user.id, entity_type="purchase_order", entity_id=order.id, action="status",
        old_values={"status": "draft"}, new_values={"status": "sent"},
    )
    archive.purchase_order_document(db, order, current_user.id, backfilled=False)
    db.commit()
    db.refresh(order)
    return order


@router.get("/{order_id}/pdf")
def get_purchase_order_pdf(
    order_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Bestellung als PDF (Entwurf live, sonst das archivierte Original)."""
    order = _get_order(db, order_id)
    try:
        content = archive.purchase_order_document(db, order, current_user.id)
        db.commit()
    except archive.ArchiveIntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="Bestellung_{order.order_number}.pdf"'},
    )


@router.post("/{order_id}/send-email", response_model=PurchaseOrderRead)
def send_purchase_order_email(
    order_id: UUID,
    payload: PurchaseOrderSendEmailIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> PurchaseOrder:
    """Bestellung per E-Mail an den Lieferanten senden. Ein Entwurf wird dabei auf „bestellt“ gesetzt."""
    from app.models.app_setting import AppSetting
    from app.services.email import send_email_with_attachment
    from app.services.purchase_order_pdf import generate_purchase_order_pdf

    order = _get_order(db, order_id)
    if order.status not in OPEN_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Diese Bestellung kann nicht mehr versendet werden")
    recipient = (payload.recipient_email or "").strip() or (order.supplier.email or "").strip()
    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Keine E-Mail-Adresse. Bitte Empfänger angeben oder beim Lieferanten hinterlegen.",
        )

    row = db.query(AppSetting).filter(AppSetting.key == "company_name").first()
    company_name = ((row.value if row else "") or "WareVision").strip()
    customer_no = (order.supplier.customer_number or "").strip()
    body = (
        "Sehr geehrte Damen und Herren,\n\n"
        f"anbei erhalten Sie unsere Bestellung {order.order_number}"
        + (f" (Kundennummer {customer_no})" if customer_no else "")
        + ".\n"
        + (f"Gewünschter Liefertermin: {order.expected_date.strftime('%d.%m.%Y')}\n" if order.expected_date else "")
        + "\nBitte bestätigen Sie die Bestellung kurz. Vielen Dank.\n\n"
        f"Mit freundlichen Grüßen\n{company_name}\n"
    )
    was_draft = order.status == "draft"
    try:
        pdf_bytes = generate_purchase_order_pdf(db, order) if was_draft else archive.purchase_order_document(db, order, current_user.id)
    except archive.ArchiveIntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    try:
        send_email_with_attachment(
            db,
            to_email=recipient,
            subject=f"Bestellung {order.order_number} – {company_name}",
            body=body,
            attachment_filename=f"Bestellung_{order.order_number}.pdf",
            attachment_data=pdf_bytes,
            attachment_content_type="application/pdf",
        )
    except Exception as exc:
        logger.exception("E-Mail-Versand fehlgeschlagen für Bestellung %s", order_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"E-Mail konnte nicht gesendet werden: {exc}",
        ) from exc

    old_status = order.status
    if order.status == "draft":
        order.status = "sent"
    order.sent_at = datetime.now(timezone.utc)
    order.sent_to_email = recipient
    if was_draft:  # genau die versendete Datei archivieren
        archive.store(db, entity_type="purchase_order", entity_id=order.id, kind="pdf",
                      document_number=order.order_number, data=pdf_bytes, user_id=current_user.id)
    log_audit(
        db, user_id=current_user.id, entity_type="purchase_order", entity_id=order.id, action="email_sent",
        old_values={"status": old_status}, new_values={"status": order.status, "recipient": recipient},
    )
    db.commit()
    db.refresh(order)
    return order


@router.post("/{order_id}/receive", response_model=PurchaseOrderRead)
def receive_goods(
    order_id: UUID,
    payload: PurchaseOrderReceiveIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PurchaseOrder:
    """Wareneingang buchen (auch Teillieferung). Artikelpositionen werden ins Lager gebucht."""
    order = _get_order(db, order_id)
    if order.status == "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Die Bestellung ist noch ein Entwurf. Bitte zuerst bestellen (E-Mail oder „Als bestellt markieren“).",
        )
    if order.status not in ("sent", "partial"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Für diese Bestellung ist kein Wareneingang mehr möglich")

    items = {it.id: it for it in order.items}
    seen: set[UUID] = set()
    booked: list[dict] = []
    delivery_note = (payload.delivery_note or "").strip()
    note = f"Wareneingang {order.order_number}" + (f", Lieferschein {delivery_note}" if delivery_note else "")
    for line in payload.lines:
        if line.item_id in seen:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Eine Position ist doppelt angegeben")
        seen.add(line.item_id)
        item = items.get(line.item_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Position gehört nicht zu dieser Bestellung")
        if line.quantity == 0:
            continue
        open_qty = item.quantity - item.received_quantity
        if line.quantity > open_qty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Position {item.position}: Es sind nur noch {open_qty} offen. "
                    "Mehrlieferungen bitte zusätzlich im Lager als Zugang buchen."
                ),
            )
        if item.article_id:
            apply_stock_change(
                db,
                article_id=item.article_id,
                quantity=line.quantity,
                movement_type="incoming",
                reference_type="purchase_order",
                reference_id=order.id,
                notes=note,
                user_id=current_user.id,
            )
            if payload.update_purchase_price:
                article = db.query(Article).filter(Article.id == item.article_id).first()
                if article is not None:
                    article.purchase_price = item.unit_price
        item.received_quantity += line.quantity
        booked.append({"position": item.position, "quantity": line.quantity})

    if not booked:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bitte mindestens eine gelieferte Menge eingeben")

    old_status = order.status
    order.status = "received" if all(it.received_quantity >= it.quantity for it in order.items) else "partial"
    log_audit(
        db, user_id=current_user.id, entity_type="purchase_order", entity_id=order.id, action="goods_receipt",
        old_values={"status": old_status},
        new_values={"status": order.status, "lines": booked, "delivery_note": delivery_note or None},
    )
    db.commit()
    db.refresh(order)
    return order


@router.post("/{order_id}/cancel", response_model=PurchaseOrderRead)
def cancel_purchase_order(
    order_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> PurchaseOrder:
    """Bestellung stornieren. Wurde schon etwas geliefert, wird sie abgeschlossen (Rest kommt nicht mehr)."""
    order = _get_order(db, order_id)
    if order.status == "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Entwürfe bitte löschen statt stornieren")
    if order.status not in ("sent", "partial"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Diese Bestellung ist bereits abgeschlossen")
    old_status = order.status
    order.status = "closed" if any(it.received_quantity > 0 for it in order.items) else "cancelled"
    log_audit(
        db, user_id=current_user.id, entity_type="purchase_order", entity_id=order.id, action="cancel",
        old_values={"status": old_status}, new_values={"status": order.status},
    )
    db.commit()
    db.refresh(order)
    return order
