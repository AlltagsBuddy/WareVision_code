"""Workshop orders API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.maintenance_plan import MaintenancePlan
from app.models.vehicle import Vehicle
from app.models.workshop_order import WorkshopOrder, WorkshopOrderItem
from app.models.user import User
from app.models.article import Article
from app.models.labor_rate import LaborRate
from app.schemas.workshop_order import (
    WorkshopOrderCreate,
    WorkshopOrderRead,
    WorkshopOrderUpdate,
    WorkshopOrderItemCreate,
    WorkshopOrderItemRead,
)
from app.services.stock_booking import (
    book_workshop_material_out,
    book_workshop_material_return,
    release_stock_for_cancelled_workshop_order,
)

router = APIRouter(prefix="/workshop-orders", tags=["workshop-orders"])


def _next_order_number(db: Session) -> str:
    """Generate next order number (e.g. WO-2026-0001)."""
    from datetime import datetime
    year = datetime.now().year
    last = (
        db.query(WorkshopOrder)
        .filter(WorkshopOrder.order_number.like(f"WO-{year}-%"))
        .order_by(WorkshopOrder.order_number.desc())
        .first()
    )
    num = 1
    if last:
        try:
            num = int(last.order_number.split("-")[-1]) + 1
        except (IndexError, ValueError):
            pass
    return f"WO-{year}-{num:04d}"


@router.get("", response_model=list[WorkshopOrderRead])
def list_workshop_orders(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    customer_id: UUID | None = None,
    vehicle_id: UUID | None = None,
    status_filter: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[WorkshopOrderRead]:
    """List workshop orders."""
    query = db.query(WorkshopOrder)
    if customer_id:
        query = query.filter(WorkshopOrder.customer_id == customer_id)
    if vehicle_id:
        query = query.filter(WorkshopOrder.vehicle_id == vehicle_id)
    if status_filter:
        query = query.filter(WorkshopOrder.status == status_filter)
    orders = query.order_by(WorkshopOrder.created_at.desc()).offset(skip).limit(limit).all()
    return [_wo_to_read(o) for o in orders]


def _find_maintenance_plan(db: Session, vehicle_id: UUID) -> MaintenancePlan | None:
    """Passenden Wartungsplan für ein Fahrzeug suchen (Hersteller+Modell, Fallback nur Hersteller)."""
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        return None
    if vehicle.vehicle_model_id:
        plan = db.query(MaintenancePlan).filter(
            MaintenancePlan.manufacturer_id == vehicle.manufacturer_id,
            MaintenancePlan.vehicle_model_id == vehicle.vehicle_model_id,
        ).first()
        if plan:
            return plan
    return db.query(MaintenancePlan).filter(
        MaintenancePlan.manufacturer_id == vehicle.manufacturer_id,
        MaintenancePlan.vehicle_model_id.is_(None),
    ).first()


def _wo_to_read(order: WorkshopOrder) -> WorkshopOrderRead:
    """WorkshopOrder in Schema umwandeln und Wartungsplan-Name befüllen."""
    data = WorkshopOrderRead.model_validate(order)
    if order.maintenance_plan:
        data.maintenance_plan_name = order.maintenance_plan.name
    return data


@router.post("", response_model=WorkshopOrderRead, status_code=status.HTTP_201_CREATED)
def create_workshop_order(
    payload: WorkshopOrderCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WorkshopOrderRead:
    """Create workshop order. Wartungsplan wird automatisch anhand Fahrzeug/Modell gesetzt."""
    order_number = _next_order_number(db)
    # Manueller Override hat Vorrang, sonst automatisch ermitteln
    if payload.maintenance_plan_id:
        plan_id = payload.maintenance_plan_id
    else:
        plan = _find_maintenance_plan(db, payload.vehicle_id)
        plan_id = plan.id if plan else None
    order = WorkshopOrder(
        customer_id=payload.customer_id,
        vehicle_id=payload.vehicle_id,
        appointment_id=payload.appointment_id,
        maintenance_plan_id=plan_id,
        order_number=order_number,
        status="new",
        complaint_description=payload.complaint_description,
        internal_notes=payload.internal_notes,
        mileage_at_checkin=payload.mileage_at_checkin,
        operating_hours_at_checkin=payload.operating_hours_at_checkin,
        estimated_work_minutes=payload.estimated_work_minutes,
        created_by=current_user.id,
    )
    db.add(order)
    db.flush()

    # Artikel aus Wartungsplan-Aufgaben automatisch als Positionen übernehmen
    if plan_id:
        plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == plan_id).first()
        if plan:
            for task in sorted(plan.tasks, key=lambda t: t.sort_order):
                if task.article_id:
                    article = db.query(Article).filter(Article.id == task.article_id).first()
                    if article:
                        db.add(WorkshopOrderItem(
                            workshop_order_id=order.id,
                            item_type="material",
                            article_id=article.id,
                            description=f"{task.name} – {article.name}",
                            quantity=task.quantity,
                            unit=task.unit or "Stück",
                            unit_price=article.sales_price_b2c,
                            vat_rate=article.vat_rate,
                            source="maintenance_plan",
                        ))

    # Arbeitszeit-Posten anlegen wenn Stundenpreis und Arbeitszeit angegeben
    if payload.labor_rate_id and payload.estimated_work_minutes:
        labor_rate = db.query(LaborRate).filter(LaborRate.id == payload.labor_rate_id).first()
        if labor_rate:
            from decimal import Decimal
            hours = Decimal(payload.estimated_work_minutes) / Decimal(60)
            hours = hours.quantize(Decimal("0.01"))
            db.add(WorkshopOrderItem(
                workshop_order_id=order.id,
                item_type="labor",
                description=labor_rate.name,
                quantity=hours,
                unit="Std.",
                unit_price=labor_rate.rate_per_hour,
                vat_rate=Decimal("19.00"),
                source="manual",
            ))

    db.commit()
    db.refresh(order)
    return _wo_to_read(order)


@router.get("/{order_id}", response_model=WorkshopOrderRead)
def get_workshop_order(
    order_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WorkshopOrderRead:
    """Get workshop order by ID."""
    order = db.query(WorkshopOrder).filter(WorkshopOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Werkstattauftrag nicht gefunden",
        )
    return _wo_to_read(order)


@router.patch("/{order_id}", response_model=WorkshopOrderRead)
def update_workshop_order(
    order_id: UUID,
    payload: WorkshopOrderUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WorkshopOrderRead:
    """Update workshop order (e.g. status)."""
    order = db.query(WorkshopOrder).filter(WorkshopOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Werkstattauftrag nicht gefunden",
        )
    if payload.customer_id is not None or payload.vehicle_id is not None:
        if order.status == "invoiced":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bereits abgerechnete Aufträge können nicht geändert werden",
            )
    if payload.customer_id is not None:
        order.customer_id = payload.customer_id
    if payload.vehicle_id is not None:
        order.vehicle_id = payload.vehicle_id
        # Wartungsplan beim Fahrzeugwechsel neu ermitteln
        plan = _find_maintenance_plan(db, payload.vehicle_id)
        order.maintenance_plan_id = plan.id if plan else None
    if payload.complaint_description is not None:
        order.complaint_description = payload.complaint_description
    if payload.status is not None:
        if payload.status == "cancelled" and order.status != "cancelled":
            release_stock_for_cancelled_workshop_order(db, order.id, current_user.id)
        order.status = payload.status
    if payload.actual_work_minutes is not None:
        order.actual_work_minutes = payload.actual_work_minutes
    if payload.internal_notes is not None:
        order.internal_notes = payload.internal_notes
    db.commit()
    db.refresh(order)
    return _wo_to_read(order)


@router.get("/{order_id}/items", response_model=list[WorkshopOrderItemRead])
def list_workshop_order_items(
    order_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[WorkshopOrderItem]:
    """List workshop order items."""
    order = db.query(WorkshopOrder).filter(WorkshopOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Werkstattauftrag nicht gefunden",
        )
    return list(order.items)


@router.post("/{order_id}/items", response_model=WorkshopOrderItemRead, status_code=status.HTTP_201_CREATED)
def create_workshop_order_item(
    order_id: UUID,
    payload: WorkshopOrderItemCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WorkshopOrderItem:
    """Add item to workshop order."""
    order = db.query(WorkshopOrder).filter(WorkshopOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Werkstattauftrag nicht gefunden",
        )
    if order.status in ("invoiced", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="In diesem Auftragsstatus können keine Positionen mehr hinzugefügt werden.",
        )
    unit_price = payload.unit_price
    if payload.item_type == "material" and payload.article_id:
        article = db.query(Article).filter(Article.id == payload.article_id).first()
        if article:
            unit_price = article.sales_price_b2c
    item = WorkshopOrderItem(
        workshop_order_id=order_id,
        item_type=payload.item_type,
        article_id=payload.article_id,
        description=payload.description,
        quantity=payload.quantity,
        unit=payload.unit or ("Stück" if payload.item_type == "material" else "Std." if payload.item_type == "labor" else None),
        unit_price=unit_price,
        vat_rate=payload.vat_rate,
        source="manual",
    )
    db.add(item)
    db.flush()
    try:
        book_workshop_material_out(db, item, current_user.id)
    except HTTPException:
        db.rollback()
        raise
    db.commit()
    db.refresh(item)
    return item


@router.get("/{order_id}/pdf")
def get_workshop_order_pdf(
    order_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Werkstattauftrag als PDF generieren (Abhak-Liste fuer die Werkstatt)."""
    from app.services.pdf import generate_workshop_order_pdf

    order = db.query(WorkshopOrder).filter(WorkshopOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Werkstattauftrag nicht gefunden",
        )
    pdf_bytes = generate_workshop_order_pdf(db, order)
    filename = f"Auftrag_{order.order_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.delete("/{order_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workshop_order_item(
    order_id: UUID,
    item_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Remove item from workshop order."""
    order = db.query(WorkshopOrder).filter(WorkshopOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Werkstattauftrag nicht gefunden",
        )
    if order.status in ("invoiced", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="In diesem Auftragsstatus können keine Positionen entfernt werden.",
        )
    item = (
        db.query(WorkshopOrderItem)
        .filter(
            WorkshopOrderItem.id == item_id,
            WorkshopOrderItem.workshop_order_id == order_id,
        )
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position nicht gefunden",
        )
    try:
        book_workshop_material_return(
            db,
            item,
            current_user.id,
            notes="Werkstattauftrag: Position entfernt",
        )
    except HTTPException:
        db.rollback()
        raise
    db.delete(item)
    db.commit()
