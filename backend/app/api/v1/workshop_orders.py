"""Workshop orders API."""

import os
import uuid
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.workshop_order_photo import WorkshopOrderPhoto
from app.services.audit import log_audit
from app.models.maintenance_plan import MaintenancePlan
from app.services.maintenance_match import find_plan_for_vehicle
from app.models.vehicle import Vehicle
from app.models.workshop_order import WorkshopOrder, WorkshopOrderItem
from app.models.user import User
from app.models.article import Article
from app.models.labor_rate import LaborRate
from app.schemas.workshop_order import (
    WorkshopOrderPhotoRead,
    WorkshopOrderPhotoUpdate,
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
    """Passenden Wartungsplan für ein Fahrzeug suchen (Modell, Hersteller, Baujahr)."""
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    return find_plan_for_vehicle(db, vehicle)


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
    log_audit(db, user_id=current_user.id, entity_type="workshop_order", entity_id=order_id, action="item_delete",
              old_values={"description": item.description, "quantity": str(item.quantity),
                          "unit_price": str(item.unit_price)})
    db.delete(item)
    db.commit()


# ---------------------------------------------------------------------------
# Fotos zum Auftrag
# ---------------------------------------------------------------------------

PHOTO_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
PHOTO_MAX_SIZE = 15 * 1024 * 1024  # 15 MB
PHOTO_MAX_COUNT = 30


def _photo_type(data: bytes) -> str | None:
    """Bildtyp anhand der Dateisignatur erkennen (nicht der Angabe des Browsers vertrauen)."""
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _photo_read(photo: WorkshopOrderPhoto) -> WorkshopOrderPhotoRead:
    return WorkshopOrderPhotoRead.model_validate(photo)


def _get_order_or_404(db: Session, order_id: UUID) -> WorkshopOrder:
    order = db.query(WorkshopOrder).filter(WorkshopOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Werkstattauftrag nicht gefunden")
    return order


@router.get("/{order_id}/photos", response_model=list[WorkshopOrderPhotoRead])
def list_order_photos(
    order_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[WorkshopOrderPhotoRead]:
    """Fotos eines Auftrags (älteste zuerst)."""
    _get_order_or_404(db, order_id)
    photos = (
        db.query(WorkshopOrderPhoto)
        .filter(WorkshopOrderPhoto.workshop_order_id == order_id)
        .order_by(WorkshopOrderPhoto.created_at)
        .all()
    )
    return [_photo_read(p) for p in photos]


@router.post("/{order_id}/photos", response_model=WorkshopOrderPhotoRead, status_code=status.HTTP_201_CREATED)
async def upload_order_photo(
    order_id: UUID,
    file: Annotated[UploadFile, File()],
    caption: Annotated[str | None, Form()] = None,
    db: Annotated[Session, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
) -> WorkshopOrderPhotoRead:
    """Foto hochladen (JPEG, PNG oder WebP, max. 15 MB, max. 30 Fotos je Auftrag)."""
    order = _get_order_or_404(db, order_id)
    count = db.query(WorkshopOrderPhoto).filter(WorkshopOrderPhoto.workshop_order_id == order_id).count()
    if count >= PHOTO_MAX_COUNT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Maximal {PHOTO_MAX_COUNT} Fotos je Auftrag")
    data = await file.read(PHOTO_MAX_SIZE + 1)
    if len(data) > PHOTO_MAX_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Foto zu groß (max. 15 MB)")
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Datei ist leer")
    content_type = _photo_type(data)
    if content_type is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Nur Fotos im Format JPEG, PNG oder WebP sind erlaubt")
    folder = Path(get_settings().UPLOAD_DIR) / "werkstattfotos" / str(order.id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{uuid.uuid4().hex}{PHOTO_TYPES[content_type]}"
    path.write_bytes(data)
    original = Path(file.filename or "foto").name[:200] or "foto"
    photo = WorkshopOrderPhoto(
        workshop_order_id=order.id,
        filename=original,
        content_type=content_type,
        file_path=str(path),
        file_size=len(data),
        caption=(caption or "").strip()[:255] or None,
        created_by=current_user.id,
    )
    db.add(photo)
    db.flush()
    log_audit(db, user_id=current_user.id, entity_type="workshop_order", entity_id=order.id,
              action="photo_add", new_values={"photo_id": str(photo.id), "filename": original})
    db.commit()
    db.refresh(photo)
    return _photo_read(photo)


def _get_photo_or_404(db: Session, order_id: UUID, photo_id: UUID) -> WorkshopOrderPhoto:
    photo = (
        db.query(WorkshopOrderPhoto)
        .filter(WorkshopOrderPhoto.id == photo_id, WorkshopOrderPhoto.workshop_order_id == order_id)
        .first()
    )
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Foto nicht gefunden")
    return photo


@router.get("/{order_id}/photos/{photo_id}")
def get_order_photo(
    order_id: UUID,
    photo_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FileResponse:
    """Fotodatei ausliefern."""
    photo = _get_photo_or_404(db, order_id, photo_id)
    if not os.path.isfile(photo.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fotodatei nicht gefunden")
    return FileResponse(path=photo.file_path, media_type=photo.content_type, filename=photo.filename,
                        content_disposition_type="inline")


@router.patch("/{order_id}/photos/{photo_id}", response_model=WorkshopOrderPhotoRead)
def update_order_photo(
    order_id: UUID,
    photo_id: UUID,
    payload: WorkshopOrderPhotoUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WorkshopOrderPhotoRead:
    """Bildunterschrift ändern."""
    photo = _get_photo_or_404(db, order_id, photo_id)
    photo.caption = (payload.caption or "").strip()[:255] or None
    db.commit()
    db.refresh(photo)
    return _photo_read(photo)


@router.delete("/{order_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order_photo(
    order_id: UUID,
    photo_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Foto entfernen (wird im Audit-Log protokolliert)."""
    photo = _get_photo_or_404(db, order_id, photo_id)
    path = photo.file_path
    log_audit(db, user_id=current_user.id, entity_type="workshop_order", entity_id=order_id,
              action="photo_delete", old_values={"photo_id": str(photo.id), "filename": photo.filename})
    db.delete(photo)
    db.commit()
    try:
        os.remove(path)
    except OSError:
        pass
