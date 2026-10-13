"""Lagerbuchungen aus Werkstattaufträgen und Rechnungen (eine DB-Transaktion, kein eigener commit)."""

from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.article import Article
from app.models.invoice import InvoiceItem
from app.models.stock_movement import StockMovement
from app.models.workshop_order import WorkshopOrderItem


def decimal_quantity_to_int_units(quantity: Decimal) -> int:
    """Positionsmenge als ganze Lagereinheit (Stück)."""
    if quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Menge muss größer als 0 sein.",
        )
    if quantity != quantity.to_integral_value():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lagerartikel: nur ganzzahlige Mengen (Stück) erlaubt.",
        )
    return int(quantity)


def workshop_line_consumes_stock(item: WorkshopOrderItem) -> bool:
    """True, wenn die Position vom Lager abgeht."""
    return item.item_type == "material" and item.article_id is not None


def apply_stock_change(
    db: Session,
    *,
    article_id: UUID,
    quantity: int,
    movement_type: str,
    reference_type: str | None,
    reference_id: UUID | None,
    notes: str | None,
    user_id: UUID | None,
) -> None:
    """quantity immer positiv; incoming = Zugang, alle anderen Typen = Abgang (wie Stock-API)."""
    if quantity <= 0:
        return
    article = db.query(Article).filter(Article.id == article_id).with_for_update().first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artikel nicht gefunden")

    sign = 1 if movement_type == "incoming" else -1
    delta = sign * quantity

    new_stock = article.stock_quantity + delta
    if new_stock < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Nicht genug Bestand. Aktuell: {article.stock_quantity}, "
                f"benötigt: {quantity}"
            ),
        )

    movement = StockMovement(
        article_id=article_id,
        movement_type=movement_type,
        quantity=quantity,
        reference_type=reference_type,
        reference_id=reference_id,
        notes=notes,
        created_by=user_id,
    )
    db.add(movement)
    article.stock_quantity = new_stock


def book_workshop_material_out(
    db: Session,
    item: WorkshopOrderItem,
    user_id: UUID | None,
) -> None:
    """Warenausgang für Materialposition im Werkstattauftrag."""
    if not workshop_line_consumes_stock(item):
        return
    qty = decimal_quantity_to_int_units(item.quantity)
    apply_stock_change(
        db,
        article_id=item.article_id,  # type: ignore[arg-type]
        quantity=qty,
        movement_type="workshop_consumption",
        reference_type="workshop_order_item",
        reference_id=item.id,
        notes="Werkstattauftrag: Material",
        user_id=user_id,
    )


def book_workshop_material_return(
    db: Session,
    item: WorkshopOrderItem,
    user_id: UUID | None,
    notes: str,
) -> None:
    """Rückbuchung (z. B. Position gelöscht oder Auftrag storniert)."""
    if not workshop_line_consumes_stock(item):
        return
    qty = decimal_quantity_to_int_units(item.quantity)
    apply_stock_change(
        db,
        article_id=item.article_id,  # type: ignore[arg-type]
        quantity=qty,
        movement_type="incoming",
        reference_type="workshop_order_item",
        reference_id=item.id,
        notes=notes,
        user_id=user_id,
    )


def release_stock_for_cancelled_workshop_order(
    db: Session,
    order_id: UUID,
    user_id: UUID | None,
) -> None:
    """Alle Lager-Materialpositionen eines Auftrags zurückbuchen (Status abgebrochen)."""
    items = (
        db.query(WorkshopOrderItem)
        .filter(WorkshopOrderItem.workshop_order_id == order_id)
        .all()
    )
    for item in items:
        book_workshop_material_return(
            db,
            item,
            user_id,
            notes="Werkstattauftrag abgebrochen",
        )


def book_standalone_invoice_on_issue(
    db: Session,
    invoice_items: list[InvoiceItem],
    user_id: UUID | None,
) -> None:
    """Beim Ausstellen einer Freirechnung (ohne Werkstattauftrag) Lager für Artikelpositionen abbuchen."""
    for it in invoice_items:
        if it.article_id is None:
            continue
        qty = decimal_quantity_to_int_units(it.quantity)
        apply_stock_change(
            db,
            article_id=it.article_id,
            quantity=qty,
            movement_type="invoice_consumption",
            reference_type="invoice_item",
            reference_id=it.id,
            notes="Rechnung ausgestellt",
            user_id=user_id,
        )


def return_stock_for_cancelled_issued_invoice(
    db: Session,
    invoice_items: list[InvoiceItem],
    user_id: UUID | None,
) -> None:
    """Nach Storno einer ausgestellten Freirechnung Bestand zurückbuchen."""
    for it in invoice_items:
        if it.article_id is None or it.quantity <= 0:
            continue
        qty = decimal_quantity_to_int_units(it.quantity)
        apply_stock_change(
            db,
            article_id=it.article_id,
            quantity=qty,
            movement_type="incoming",
            reference_type="invoice_item",
            reference_id=it.id,
            notes="Storno Rechnung",
            user_id=user_id,
        )
