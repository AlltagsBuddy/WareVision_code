"""Invoices API."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.invoice import Invoice, InvoiceItem
from app.models.workshop_order import WorkshopOrder, WorkshopOrderItem
from app.models.user import User
from app.schemas.invoice import InvoiceCreate, InvoiceRead, InvoiceItemRead

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
    """Create invoice items from workshop order, return (net_amount, vat_amount)."""
    items = db.query(WorkshopOrderItem).filter(WorkshopOrderItem.workshop_order_id == workshop_order_id).all()
    net = Decimal(0)
    vat_total = Decimal(0)
    for wo_item in items:
        line_net = wo_item.quantity * wo_item.unit_price
        line_vat = line_net * (wo_item.vat_rate / 100)
        inv_item = InvoiceItem(
            invoice_id=invoice_id,
            workshop_order_item_id=wo_item.id,
            article_id=wo_item.article_id,
            description=wo_item.description,
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
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
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
            Invoice.due_date.isnot(None),
            Invoice.due_date < today,
        )
    return query.order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
def create_invoice(
    payload: InvoiceCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Invoice:
    """Create invoice. If workshop_order_id given, items are copied from the order."""
    invoice_number = _next_invoice_number(db)
    due_date = payload.due_date or payload.invoice_date + timedelta(days=14)

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
        net, vat = _create_items_from_workshop_order(db, inv.id, payload.workshop_order_id)
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

    db.commit()
    db.refresh(inv)
    return inv


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


@router.post("/{invoice_id}/mark-paid", response_model=InvoiceRead)
def mark_invoice_paid(
    invoice_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
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
    db.commit()
    db.refresh(inv)
    return inv


@router.post("/{invoice_id}/issue", response_model=InvoiceRead)
def issue_invoice(
    invoice_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Invoice:
    """Set invoice status to issued."""
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rechnung nicht gefunden")
    if inv.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nur Entwürfe können ausgestellt werden")
    inv.status = "issued"
    db.commit()
    db.refresh(inv)
    return inv


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
    pdf_bytes = generate_invoice_pdf(db, inv)
    return Response(content=pdf_bytes, media_type="application/pdf")


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
    pdf_bytes = generate_zugferd_pdf(db, inv)
    filename = f"Rechnung_{inv.invoice_number}_ZUGFeRD.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
