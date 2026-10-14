"""Invoices API."""

import logging
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.invoice import Invoice, InvoiceItem
from app.models.workshop_order import WorkshopOrder, WorkshopOrderItem
from app.models.user import User
from app.schemas.invoice import InvoiceCorrectionIn, InvoiceCreate, InvoiceRead, InvoiceItemRead
from app.services.audit import log_audit
from app.services.stock_booking import (
    apply_stock_change,
    book_standalone_invoice_on_issue,
    decimal_quantity_to_int_units,
    return_stock_for_cancelled_issued_invoice,
)

logger = logging.getLogger(__name__)

_CENT = Decimal("0.01")


def _recalc_totals(db: Session, inv: Invoice) -> None:
    """Netto, MwSt und Brutto aus den Positionen berechnen.
    MwSt je Steuersatz kaufmännisch gerundet (§ 14 Abs. 4 Nr. 8 UStG, EN 16931 BR-CO-14),
    damit PDF, E-Rechnung und Datenbank exakt übereinstimmen."""
    db.flush()
    items = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == inv.id).all()
    bases: dict[Decimal, Decimal] = {}
    for it in items:
        rate = Decimal(it.vat_rate).quantize(_CENT)
        bases[rate] = bases.get(rate, Decimal("0")) + Decimal(it.line_total_net).quantize(_CENT, rounding=ROUND_HALF_UP)
    net = sum(bases.values(), Decimal("0"))
    vat = sum(((b * r / 100).quantize(_CENT, rounding=ROUND_HALF_UP) for r, b in bases.items()), Decimal("0"))
    inv.net_amount = net
    inv.vat_amount = vat
    inv.gross_amount = net + vat

router = APIRouter(prefix="/invoices", tags=["invoices"])


def _next_invoice_number(db: Session) -> str:
    """Generate next invoice number (e.g. RE-2026-0001)."""
    year = date.today().year
    last = (
        db.query(Invoice)
        .filter(Invoice.invoice_number.like(f"RE-{year}-%"))
        .order_by(Invoice.invoice_number.desc())
        .first()
    )
    num = 1
    if last:
        try:
            num = int(last.invoice_number.split("-")[-1]) + 1
        except (IndexError, ValueError):
            pass
    return f"RE-{year}-{num:04d}"


def _create_items_from_workshop_order(db: Session, invoice_id: UUID, workshop_order_id: UUID) -> tuple[Decimal, Decimal]:
    """Rechnungspositionen aus Werkstattauftrag kopieren. Gibt (netto, mwst) zurück.
    Positionen ohne Beschreibung werden übersprungen. Wirft ValueError wenn keine Positionen vorhanden."""
    items = db.query(WorkshopOrderItem).filter(WorkshopOrderItem.workshop_order_id == workshop_order_id).all()
    billable = [i for i in items if (i.description or "").strip()]
    if not billable:
        raise ValueError("Der Werkstattauftrag enthält keine fakturierbaren Positionen")
    net = Decimal(0)
    vat_total = Decimal(0)
    for wo_item in billable:
        line_net = wo_item.quantity * wo_item.unit_price
        line_vat = line_net * (wo_item.vat_rate / 100)
        inv_item = InvoiceItem(
            invoice_id=invoice_id,
            workshop_order_item_id=wo_item.id,
            article_id=wo_item.article_id,
            description=wo_item.description.strip(),
            quantity=wo_item.quantity,
            unit=wo_item.unit,
            unit_price=wo_item.unit_price,
            vat_rate=wo_item.vat_rate,
            line_total_net=line_net,
        )
        db.add(inv_item)
        net += line_net
        vat_total += line_vat
    return net, vat_total


@router.get("", response_model=list[InvoiceRead])
def list_invoices(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    customer_id: UUID | None = None,
    status_filter: str | None = None,
    overdue: bool = False,
    date_from: date | None = None,
    date_to: date | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
) -> list[Invoice]:
    """List invoices. overdue=True: nur überfällige (issued/partially_paid, due_date < today)."""
    query = db.query(Invoice)
    if customer_id:
        query = query.filter(Invoice.customer_id == customer_id)
    if status_filter:
        query = query.filter(Invoice.status == status_filter)
    if overdue:
        today = date.today()
        query = query.filter(
            Invoice.status.in_(["issued", "partially_paid"]),
            Invoice.document_type == "invoice",
            Invoice.due_date.isnot(None),
            Invoice.due_date < today,
        )
    if date_from:
        query = query.filter(Invoice.invoice_date >= date_from)
    if date_to:
        query = query.filter(Invoice.invoice_date <= date_to)
    return query.order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
def create_invoice(
    payload: InvoiceCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> Invoice:
    """Create invoice. If workshop_order_id given, items are copied from the order."""
    invoice_number = _next_invoice_number(db)
    due_date = payload.due_date or payload.invoice_date + timedelta(days=14)
    # Leistungsdatum: ohne Angabe gilt das Rechnungsdatum (§ 14 Abs. 4 Nr. 6 UStG)
    service_date = payload.service_date or payload.invoice_date

    if payload.workshop_order_id:
        order = db.query(WorkshopOrder).filter(WorkshopOrder.id == payload.workshop_order_id).first()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Werkstattauftrag nicht gefunden")
        if order.status == "invoiced":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Für diesen Werkstattauftrag existiert bereits eine Rechnung",
            )
        if order.customer_id != payload.customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kunde stimmt nicht mit Werkstattauftrag überein",
            )
        inv = Invoice(
            customer_id=payload.customer_id,
            workshop_order_id=payload.workshop_order_id,
            invoice_number=invoice_number,
            invoice_date=payload.invoice_date,
            service_date=service_date,
            due_date=due_date,
            status="draft",
            currency="EUR",
            net_amount=0,
            vat_amount=0,
            gross_amount=0,
            notes=payload.notes,
            created_by=current_user.id,
        )
        db.add(inv)
        db.flush()
        try:
            net, vat = _create_items_from_workshop_order(db, inv.id, payload.workshop_order_id)
        except ValueError as exc:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        inv.net_amount = net
        inv.vat_amount = vat
        inv.gross_amount = net + vat
        order.status = "invoiced"
    else:
        if not payload.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Positionen erforderlich (oder workshop_order_id angeben)",
            )
        net = Decimal(0)
        vat_total = Decimal(0)
        inv = Invoice(
            customer_id=payload.customer_id,
            workshop_order_id=None,
            invoice_number=invoice_number,
            invoice_date=payload.invoice_date,
            service_date=service_date,
            due_date=due_date,
            status="draft",
            currency="EUR",
            net_amount=0,
            vat_amount=0,
            gross_amount=0,
            notes=payload.notes,
            created_by=current_user.id,
        )
        db.add(inv)
        db.flush()
        for it in payload.items:
            line_net = it.quantity * it.unit_price
            line_vat = line_net * (it.vat_rate / 100)
            db.add(InvoiceItem(
                invoice_id=inv.id,
                article_id=it.article_id,
                description=it.description,
                quantity=it.quantity,
                unit=it.unit,
                unit_price=it.unit_price,
                vat_rate=it.vat_rate,
                line_total_net=line_net,
            ))
            net += line_net
            vat_total += line_vat
        inv.net_amount = net
        inv.vat_amount = vat_total
        inv.gross_amount = net + vat_total

    _recalc_totals(db, inv)

    log_audit(
        db,
        user_id=current_user.id,
        entity_type="invoice",
        entity_id=inv.id,
        action="create",
        new_values={"invoice_number": inv.invoice_number, "customer_id": str(inv.customer_id)},
    )
    db.commit()
    db.refresh(inv)
    return inv


@router.post("/zugferd/import")
async def import_zugferd(
    file: UploadFile = File(...),
    current_user: Annotated[User, Depends(get_current_user)] = None,
) -> dict:
    """ZUGFeRD/Factur-X-PDF hochladen und eingebettete Rechnungsdaten als JSON zurückgeben."""
    from app.services.zugferd import parse_zugferd_pdf

    if file.content_type not in ("application/pdf", "application/octet-stream") and not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur PDF-Dateien werden akzeptiert",
        )
    pdf_bytes = await file.read()
    if len(pdf_bytes) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Datei ist leer")
    try:
        data = parse_zugferd_pdf(pdf_bytes)
    except Exception as exc:
        logger.exception("ZUGFeRD-Import fehlgeschlagen: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"ZUGFeRD-XML konnte nicht gelesen werden: {exc}",
        ) from exc
    return data


@router.get("/{invoice_id}", response_model=InvoiceRead)
def get_invoice(
    invoice_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Invoice:
    """Get invoice by ID."""
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rechnung nicht gefunden")
    return inv


@router.get("/{invoice_id}/items", response_model=list[InvoiceItemRead])
def get_invoice_items(
    invoice_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[InvoiceItem]:
    """Get invoice items."""
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rechnung nicht gefunden")
    return inv.items


@router.post("/{invoice_id}/reminder", response_model=InvoiceRead)
def mark_invoice_reminder(
    invoice_id: UUID,
    reminder_level: int = Query(1, ge=1, le=3, description="1=1.Mahnung, 2=2., 3=3."),
    db: Annotated[Session, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
) -> Invoice:
    """Mahnstufe setzen (1., 2. oder 3. Mahnung)."""
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rechnung nicht gefunden")
    if inv.status not in ("issued", "partially_paid") or inv.document_type != "invoice":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur ausgestellte Rechnungen können gemahnt werden",
        )
    inv.reminder_level = reminder_level
    inv.reminder_date = date.today()
    log_audit(db, user_id=current_user.id, entity_type="invoice", entity_id=inv.id, action="reminder", new_values={"reminder_level": reminder_level})
    db.commit()
    db.refresh(inv)
    return inv


@router.get("/{invoice_id}/reminder-pdf")
def get_reminder_pdf(
    invoice_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Mahnbrief als PDF herunterladen (basiert auf aktueller Mahnstufe)."""
    from app.services.pdf import generate_reminder_pdf

    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rechnung nicht gefunden")
    if inv.reminder_level == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Für diese Rechnung wurde noch keine Mahnung erstellt",
        )
    pdf_bytes = generate_reminder_pdf(db, inv)
    subjects = {1: "Zahlungserinnerung", 2: "1_Mahnung", 3: "2_Mahnung"}
    label = subjects.get(inv.reminder_level, f"Mahnung_{inv.reminder_level}")
    filename = f"{label}_{inv.invoice_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{invoice_id}/mark-paid", response_model=InvoiceRead)
def mark_invoice_paid(
    invoice_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> Invoice:
    """Set invoice status to paid."""
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rechnung nicht gefunden")
    if inv.status not in ("issued", "partially_paid"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur ausgestellte Rechnungen können als bezahlt markiert werden",
        )
    inv.status = "paid"
    log_audit(db, user_id=current_user.id, entity_type="invoice", entity_id=inv.id, action="mark_paid")
    db.commit()
    db.refresh(inv)
    return inv


@router.post("/{invoice_id}/issue", response_model=InvoiceRead)
def issue_invoice(
    invoice_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> Invoice:
    """Set invoice status to issued."""
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rechnung nicht gefunden")
    if inv.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nur Entwürfe können ausgestellt werden")
    # Freirechnung: Lager beim Ausstellen abbuchen. WO-Rechnung: Bestand wurde über Auftragspositionen gebucht.
    if inv.workshop_order_id is None:
        try:
            book_standalone_invoice_on_issue(db, list(inv.items), current_user.id)
        except HTTPException:
            db.rollback()
            raise
    inv.status = "issued"
    log_audit(db, user_id=current_user.id, entity_type="invoice", entity_id=inv.id, action="issue")
    db.commit()
    db.refresh(inv)
    return inv


@router.post("/{invoice_id}/cancel", response_model=InvoiceRead)
def cancel_invoice(
    invoice_id: UUID,
    reason: str = Body(default="", embed=True),
    db: Annotated[Session, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(require_admin)] = None,
) -> Invoice:
    """GoBD-konforme Stornierung: Erstellt eine Stornorechnung mit negativen Beträgen.
    Die Originalrechnung wird als 'cancelled' markiert und referenziert die Stornorechnung.
    Stornierbar: draft, issued, partially_paid (nicht: paid, cancelled)."""
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rechnung nicht gefunden")
    if inv.status in ("cancelled",):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rechnung ist bereits storniert",
        )
    if inv.cancellation_invoice_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Für diese Rechnung existiert bereits eine Stornorechnung",
        )
    if inv.document_type == "cancellation":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Eine Stornorechnung kann nicht storniert werden",
        )
    if inv.document_type == "invoice" and _active_corrections(db, inv):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Zu dieser Rechnung gibt es bereits Rechnungskorrekturen. "
                "Bitte die restlichen Positionen ebenfalls per Rechnungskorrektur gutschreiben."
            ),
        )

    stock_return_for_standalone = (
        inv.document_type == "invoice"
        and inv.workshop_order_id is None
        and inv.status in ("issued", "partially_paid", "paid")
    )

    # Stornonummer generieren: STO-2026-0001
    year = date.today().year
    last_sto = (
        db.query(Invoice)
        .filter(Invoice.invoice_number.like(f"STO-{year}-%"))
        .order_by(Invoice.invoice_number.desc())
        .first()
    )
    sto_num = 1
    if last_sto:
        try:
            sto_num = int(last_sto.invoice_number.split("-")[-1]) + 1
        except (IndexError, ValueError):
            pass
    sto_number = f"STO-{year}-{sto_num:04d}"

    label = "Rechnungskorrektur" if inv.document_type == "correction" else "Rechnung"
    sto_notes = f"Stornorechnung zu {label} {inv.invoice_number}"
    if reason:
        sto_notes += f". Grund: {reason}"

    storno = Invoice(
        customer_id=inv.customer_id,
        workshop_order_id=None,
        cancellation_of_id=inv.id,
        document_type="cancellation",
        invoice_number=sto_number,
        invoice_date=date.today(),
        service_date=inv.service_date,
        due_date=date.today(),
        status="issued",
        currency=inv.currency,
        net_amount=-inv.net_amount,
        vat_amount=-inv.vat_amount,
        gross_amount=-inv.gross_amount,
        notes=sto_notes,
        created_by=current_user.id,
    )
    db.add(storno)
    db.flush()

    # Positionen mit negierten Mengen kopieren
    for item in inv.items:
        db.add(InvoiceItem(
            invoice_id=storno.id,
            article_id=item.article_id,
            workshop_order_item_id=None,
            description=item.description,
            quantity=-item.quantity,
            unit=item.unit,
            unit_price=item.unit_price,
            vat_rate=item.vat_rate,
            line_total_net=-item.line_total_net,
        ))

    # Originalrechnung stornieren und Querverweis setzen
    inv.status = "cancelled"
    inv.cancellation_invoice_id = storno.id

    # Werkstattauftrag wieder auf "completed" setzen, damit erneut fakturiert werden kann
    if inv.workshop_order_id:
        order = db.query(WorkshopOrder).filter(WorkshopOrder.id == inv.workshop_order_id).first()
        if order and order.status == "invoiced":
            order.status = "completed"

    log_audit(
        db,
        user_id=current_user.id,
        entity_type="invoice",
        entity_id=inv.id,
        action="cancel",
        new_values={
            "cancellation_invoice_number": sto_number,
            "cancellation_invoice_id": str(storno.id),
            "reason": reason or None,
        },
    )
    try:
        if stock_return_for_standalone:
            return_stock_for_cancelled_issued_invoice(db, list(inv.items), current_user.id)
        if inv.document_type == "correction":
            # Storno einer Rechnungskorrektur: zurückgenommene Teile wieder aus dem Lager buchen
            for it in inv.items:
                if it.returned_to_stock and it.article_id:
                    apply_stock_change(
                        db,
                        article_id=it.article_id,
                        quantity=decimal_quantity_to_int_units(-it.quantity),
                        movement_type="invoice_consumption",
                        reference_type="invoice_item",
                        reference_id=it.id,
                        notes=f"Storno Rechnungskorrektur {inv.invoice_number}",
                        user_id=current_user.id,
                    )
    except HTTPException:
        db.rollback()
        raise
    db.commit()
    db.refresh(inv)
    return inv


# ---------------------------------------------------------------------------
# Rechnungskorrektur (Gutschrift des Verkäufers)
# ---------------------------------------------------------------------------

def _active_corrections(db: Session, original: Invoice) -> list[Invoice]:
    """Nicht stornierte Rechnungskorrekturen zu einer Rechnung."""
    return (
        db.query(Invoice)
        .filter(
            Invoice.corrects_invoice_id == original.id,
            Invoice.document_type == "correction",
            Invoice.status != "cancelled",
        )
        .order_by(Invoice.invoice_date, Invoice.invoice_number)
        .all()
    )


def _correction_state(db: Session, original: Invoice) -> dict:
    """Bereits gutgeschriebene Mengen je Position und Summen."""
    corrections = _active_corrections(db, original)
    credited_qty: dict[UUID, Decimal] = {}
    credited_gross = Decimal("0")
    for c in corrections:
        credited_gross += -Decimal(c.gross_amount)
        for it in c.items:
            if it.corrects_item_id:
                credited_qty[it.corrects_item_id] = credited_qty.get(it.corrects_item_id, Decimal("0")) + (-Decimal(it.quantity))
    return {"corrections": corrections, "credited_qty": credited_qty, "credited_gross": credited_gross}


def _next_correction_number(db: Session) -> str:
    """Nächste Nummer für Rechnungskorrekturen (eigener fortlaufender Nummernkreis, z. B. RK-2026-0001)."""
    year = date.today().year
    last = (
        db.query(Invoice)
        .filter(Invoice.invoice_number.like(f"RK-{year}-%"))
        .order_by(Invoice.invoice_number.desc())
        .first()
    )
    num = 1
    if last:
        try:
            num = int(last.invoice_number.split("-")[-1]) + 1
        except (IndexError, ValueError):
            pass
    return f"RK-{year}-{num:04d}"


def _get_correctable(db: Session, invoice_id: UUID) -> Invoice:
    """Rechnung laden und prüfen, ob sie korrigiert werden darf."""
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rechnung nicht gefunden")
    if inv.document_type != "invoice":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur normale Rechnungen können korrigiert werden (keine Storno- oder Korrekturbelege)",
        )
    if inv.status not in ("issued", "partially_paid", "paid"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur ausgestellte oder bezahlte Rechnungen können korrigiert werden. Entwürfe bitte direkt ändern.",
        )
    return inv


@router.get("/{invoice_id}/correction-info")
def get_correction_info(
    invoice_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Übersicht für eine Rechnungskorrektur: noch gutschreibbare Mengen und bisherige Korrekturen."""
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rechnung nicht gefunden")
    state = _correction_state(db, inv)
    items = []
    for it in inv.items:
        credited = state["credited_qty"].get(it.id, Decimal("0"))
        items.append({
            "item_id": str(it.id),
            "article_id": str(it.article_id) if it.article_id else None,
            "description": it.description,
            "quantity": str(it.quantity),
            "credited_quantity": str(credited),
            "remaining_quantity": str(Decimal(it.quantity) - credited),
            "unit": it.unit,
            "unit_price": str(it.unit_price),
            "vat_rate": str(it.vat_rate),
        })
    gross = Decimal(inv.gross_amount)
    return {
        "invoice_id": str(inv.id),
        "invoice_number": inv.invoice_number,
        "gross_amount": str(gross),
        "credited_gross": str(state["credited_gross"]),
        "remaining_gross": str(gross - state["credited_gross"]),
        "vat_rates": [str(r) for r in sorted({Decimal(it.vat_rate).quantize(_CENT) for it in inv.items}, reverse=True)],
        "items": items,
        "corrections": [
            {"id": str(c.id), "invoice_number": c.invoice_number, "invoice_date": c.invoice_date.isoformat(),
             "gross_amount": str(c.gross_amount), "status": c.status}
            for c in state["corrections"]
        ],
    }


@router.post("/{invoice_id}/correction", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
def create_correction(
    invoice_id: UUID,
    payload: InvoiceCorrectionIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> Invoice:
    """Rechnungskorrektur (Gutschrift) erstellen: einzelne Positionen/Mengen und/oder ein Preisnachlass.

    Die Originalrechnung bleibt unverändert (GoBD). Die Korrektur erhält eine eigene Nummer (RK-…),
    negative Beträge und verweist auf Nummer und Datum der Originalrechnung (§ 31 Abs. 5 UStDV).
    """
    original = _get_correctable(db, invoice_id)
    if not payload.lines and not payload.free_lines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bitte mindestens eine Position oder einen Nachlass angeben",
        )
    state = _correction_state(db, original)
    items_by_id = {it.id: it for it in original.items}
    allowed_rates = {Decimal(it.vat_rate).quantize(_CENT) for it in original.items}

    # 1. Alles prüfen und berechnen, bevor etwas gespeichert wird
    new_items: list[dict] = []
    seen: set[UUID] = set()
    for line in payload.lines:
        if line.item_id in seen:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Eine Position ist doppelt angegeben")
        seen.add(line.item_id)
        orig_item = items_by_id.get(line.item_id)
        if orig_item is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Position gehört nicht zu dieser Rechnung")
        remaining = Decimal(orig_item.quantity) - state["credited_qty"].get(orig_item.id, Decimal("0"))
        if line.quantity > remaining:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"„{orig_item.description}“: Es können höchstens {remaining.normalize():f} gutgeschrieben werden.",
            )
        stock_qty = 0
        if line.return_to_stock:
            if not orig_item.article_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"„{orig_item.description}“ ist kein Lagerartikel und kann nicht ins Lager zurückgebucht werden",
                )
            stock_qty = decimal_quantity_to_int_units(line.quantity)
        new_items.append({
            "article_id": orig_item.article_id,
            "description": orig_item.description,
            "quantity": -line.quantity,
            "unit": orig_item.unit,
            "unit_price": Decimal(orig_item.unit_price),
            "vat_rate": Decimal(orig_item.vat_rate).quantize(_CENT),
            "line_total_net": -(line.quantity * Decimal(orig_item.unit_price)).quantize(_CENT, rounding=ROUND_HALF_UP),
            "corrects_item_id": orig_item.id,
            "returned_to_stock": line.return_to_stock,
            "_stock_qty": stock_qty,
        })
    for free in payload.free_lines:
        rate = free.vat_rate.quantize(_CENT)
        if rate not in allowed_rates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Der Nachlass muss einen Steuersatz der Originalrechnung haben",
            )
        new_items.append({
            "article_id": None,
            "description": free.description,
            "quantity": Decimal("-1"),
            "unit": None,
            "unit_price": free.net_amount,
            "vat_rate": rate,
            "line_total_net": -free.net_amount,
            "corrects_item_id": None,
            "returned_to_stock": False,
            "_stock_qty": 0,
        })

    # Summen wie in _recalc_totals (MwSt je Steuersatz kaufmännisch gerundet)
    bases: dict[Decimal, Decimal] = {}
    for it in new_items:
        bases[it["vat_rate"]] = bases.get(it["vat_rate"], Decimal("0")) + it["line_total_net"]
    gross = sum(bases.values(), Decimal("0")) + sum(
        ((b * r / 100).quantize(_CENT, rounding=ROUND_HALF_UP) for r, b in bases.items()), Decimal("0")
    )
    if Decimal(original.gross_amount) - state["credited_gross"] + gross < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Die Gutschriften wären höher als der Rechnungsbetrag",
        )

    # 2. Beleg speichern
    correction = Invoice(
        customer_id=original.customer_id,
        workshop_order_id=None,
        corrects_invoice_id=original.id,
        document_type="correction",
        invoice_number=_next_correction_number(db),
        invoice_date=date.today(),
        service_date=original.service_date,
        due_date=date.today(),
        status="issued",
        currency=original.currency,
        net_amount=0,
        vat_amount=0,
        gross_amount=0,
        notes=(
            f"Rechnungskorrektur zu Rechnung {original.invoice_number} vom "
            f"{original.invoice_date.strftime('%d.%m.%Y')}. Grund: {payload.reason}"
        ),
        created_by=current_user.id,
    )
    db.add(correction)
    db.flush()
    stock_returns: list[tuple[InvoiceItem, int]] = []
    for data in new_items:
        stock_qty = data.pop("_stock_qty")
        item = InvoiceItem(invoice_id=correction.id, **data)
        db.add(item)
        if stock_qty:
            stock_returns.append((item, stock_qty))
    _recalc_totals(db, correction)

    # 3. Zurückgenommene Teile ins Lager buchen
    for item, qty in stock_returns:
        apply_stock_change(
            db,
            article_id=item.article_id,
            quantity=qty,
            movement_type="incoming",
            reference_type="invoice_item",
            reference_id=item.id,
            notes=f"Rücknahme lt. Rechnungskorrektur {correction.invoice_number}",
            user_id=current_user.id,
        )

    log_audit(
        db,
        user_id=current_user.id,
        entity_type="invoice",
        entity_id=original.id,
        action="correction",
        new_values={
            "correction_invoice_number": correction.invoice_number,
            "correction_invoice_id": str(correction.id),
            "gross_amount": str(correction.gross_amount),
            "reason": payload.reason,
        },
    )
    db.commit()
    db.refresh(correction)
    return correction


@router.get("/{invoice_id}/pdf")
def get_invoice_pdf(
    invoice_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Generate and return invoice as PDF."""
    from app.services.pdf import generate_invoice_pdf

    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rechnung nicht gefunden")
    try:
        pdf_bytes = generate_invoice_pdf(db, inv)
    except Exception as exc:
        logger.exception("PDF-Generierung fehlgeschlagen für Rechnung %s", invoice_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF konnte nicht erstellt werden: {exc}",
        ) from exc
    return Response(content=pdf_bytes, media_type="application/pdf")


@router.post("/{invoice_id}/send-email")
def send_invoice_email(
    invoice_id: UUID,
    payload: dict = Body(default_factory=dict),
    db: Annotated[Session, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Rechnung per E-Mail versenden. recipient_email optional (sonst Kunden-E-Mail)."""
    from app.services.pdf import generate_invoice_pdf
    from app.services.email import send_email_with_attachment
    from app.models.app_setting import AppSetting

    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rechnung nicht gefunden")

    recipient = (payload or {}).get("recipient_email", "").strip() if payload else ""
    if not recipient:
        cust = inv.customer
        recipient = (cust.email or "").strip()
    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Keine E-Mail-Adresse. Bitte Empfänger angeben oder Kunde hat keine E-Mail.",
        )

    settings_rows = db.query(AppSetting).filter(AppSetting.key == "company_name").all()
    company_name = (settings_rows[0].value or "WareVision").strip() if settings_rows else "WareVision"

    try:
        pdf_bytes = generate_invoice_pdf(db, inv)
    except Exception as exc:
        logger.exception("PDF-Generierung fehlgeschlagen für Rechnung %s", invoice_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF konnte nicht erstellt werden: {exc}",
        ) from exc

    doc_title = {"cancellation": "Stornorechnung", "correction": "Rechnungskorrektur"}.get(inv.document_type, "Rechnung")
    filename = f"{doc_title}_{inv.invoice_number}.pdf"
    subject = f"{doc_title} {inv.invoice_number} – {company_name}"
    ref = inv.referenced_invoice
    ref_text = f" zur Rechnung {ref.invoice_number} vom {ref.invoice_date.strftime('%d.%m.%Y')}" if ref else ""
    body = f"""Sehr geehrte Damen und Herren,

anbei erhalten Sie die {doc_title} {inv.invoice_number}{ref_text}.

Mit freundlichen Grüßen
{company_name}
"""

    try:
        send_email_with_attachment(
            db,
            to_email=recipient,
            subject=subject,
            body=body,
            attachment_filename=filename,
            attachment_data=pdf_bytes,
            attachment_content_type="application/pdf",
        )
    except Exception as exc:
        logger.exception("E-Mail-Versand fehlgeschlagen für Rechnung %s an %s", invoice_id, recipient)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"E-Mail konnte nicht gesendet werden: {exc}",
        ) from exc

    from datetime import datetime, timezone
    log_audit(
        db,
        user_id=current_user.id,
        entity_type="invoice",
        entity_id=inv.id,
        action="email_sent",
        new_values={
            "recipient_email": recipient,
            "subject": subject,
            "attachment_filename": filename,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    db.commit()

    return {"message": f"{doc_title} wurde per E-Mail versendet.", "recipient": recipient}


@router.get("/{invoice_id}/zugferd")
def get_invoice_zugferd(
    invoice_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Generate and return invoice as ZUGFeRD/Factur-X PDF (e-invoice with embedded XML)."""
    from app.services.zugferd import generate_zugferd_pdf

    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rechnung nicht gefunden")
    try:
        pdf_bytes = generate_zugferd_pdf(db, inv)
    except Exception as exc:
        logger.exception("ZUGFeRD-Generierung fehlgeschlagen für Rechnung %s", invoice_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ZUGFeRD-PDF konnte nicht erstellt werden: {exc}",
        ) from exc
    filename = f"Rechnung_{inv.invoice_number}_ZUGFeRD.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
