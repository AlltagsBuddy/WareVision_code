"""Maintenance plans API."""

import os
import uuid
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, module_guard
from app.core.config import get_settings
from app.core.database import get_db
from app.models.document import Document
from app.models.maintenance_plan import MaintenancePlan, MaintenanceTask
from app.models.vehicle import Vehicle
from app.models.user import User
from app.services.maintenance_match import find_plan_for_vehicle
from app.schemas.maintenance import (
    MaintenancePlanCreate,
    MaintenancePlanRead,
    MaintenancePlanUpdate,
    MaintenanceTaskCreate,
    MaintenanceTaskRead,
    MaintenanceTaskUpdate,
)

ALLOWED_DOCUMENT_TYPES = {"application/pdf", "image/jpeg", "image/png"}
MAX_DOCUMENT_SIZE = 20 * 1024 * 1024  # 20 MB

router = APIRouter(prefix="/maintenance-plans", tags=["maintenance-plans"], dependencies=[Depends(module_guard("maintenance_plans"))])


@router.get("", response_model=list[MaintenancePlanRead])
def list_maintenance_plans(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    manufacturer_id: UUID | None = None,
    vehicle_model_id: UUID | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[MaintenancePlanRead]:
    """List maintenance plans."""
    query = db.query(MaintenancePlan)
    if manufacturer_id:
        query = query.filter(MaintenancePlan.manufacturer_id == manufacturer_id)
    if vehicle_model_id:
        query = query.filter(MaintenancePlan.vehicle_model_id == vehicle_model_id)
    plans = query.order_by(MaintenancePlan.name).offset(skip).limit(limit).all()
    return [MaintenancePlanRead.from_orm_with_document(p) for p in plans]


@router.get("/for-vehicle/{vehicle_id}", response_model=MaintenancePlanRead | None)
def get_plan_for_vehicle(
    vehicle_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MaintenancePlanRead | None:
    """Passenden Wartungsplan suchen: Modell vor Hersteller, passender Baujahr-Bereich vor „alle Baujahre“."""
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        return None
    plan = find_plan_for_vehicle(db, vehicle)
    return MaintenancePlanRead.from_orm_with_document(plan) if plan else None


@router.post("", response_model=MaintenancePlanRead, status_code=status.HTTP_201_CREATED)
def create_maintenance_plan(
    payload: MaintenancePlanCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MaintenancePlanRead:
    """Create maintenance plan."""
    plan = MaintenancePlan(
        manufacturer_id=payload.manufacturer_id,
        vehicle_model_id=payload.vehicle_model_id,
        name=payload.name,
        description=payload.description,
        interval_km=payload.interval_km,
        interval_hours=payload.interval_hours,
        interval_months=payload.interval_months,
        build_year_from=payload.build_year_from,
        build_year_to=payload.build_year_to,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return MaintenancePlanRead.from_orm_with_document(plan)


@router.get("/{plan_id}", response_model=MaintenancePlanRead)
def get_maintenance_plan(
    plan_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MaintenancePlanRead:
    """Get maintenance plan by ID."""
    plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wartungsplan nicht gefunden",
        )
    return MaintenancePlanRead.from_orm_with_document(plan)


@router.patch("/{plan_id}", response_model=MaintenancePlanRead)
def update_maintenance_plan(
    plan_id: UUID,
    payload: MaintenancePlanUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MaintenancePlanRead:
    """Wartungsplan aktualisieren."""
    plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wartungsplan nicht gefunden",
        )
    fields = payload.model_fields_set
    year_from = payload.build_year_from if "build_year_from" in fields else plan.build_year_from
    year_to = payload.build_year_to if "build_year_to" in fields else plan.build_year_to
    if year_from is not None and year_to is not None and year_from > year_to:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Baujahr von darf nicht größer als Baujahr bis sein")
    if payload.name is not None:
        plan.name = payload.name
    if payload.description is not None:
        plan.description = payload.description
    if payload.interval_km is not None:
        plan.interval_km = payload.interval_km
    if payload.interval_hours is not None:
        plan.interval_hours = payload.interval_hours
    if payload.interval_months is not None:
        plan.interval_months = payload.interval_months
    # Modell und Baujahr dürfen auch geleert werden (null = alle Modelle / alle Baujahre)
    if "vehicle_model_id" in fields:
        plan.vehicle_model_id = payload.vehicle_model_id
    plan.build_year_from = year_from
    plan.build_year_to = year_to
    db.commit()
    db.refresh(plan)
    return MaintenancePlanRead.from_orm_with_document(plan)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_maintenance_plan(
    plan_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Delete maintenance plan."""
    plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wartungsplan nicht gefunden",
        )
    db.delete(plan)
    db.commit()


def _task_to_read(task: MaintenanceTask) -> MaintenanceTaskRead:
    """Task in Schema umwandeln und Artikelname befüllen."""
    obj = MaintenanceTaskRead.model_validate(task)
    if task.article:
        obj.article_name = task.article.name
        obj.article_number = task.article.article_number
    return obj


@router.get("/{plan_id}/tasks", response_model=list[MaintenanceTaskRead])
def list_maintenance_tasks(
    plan_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[MaintenanceTaskRead]:
    """List tasks of a maintenance plan."""
    plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wartungsplan nicht gefunden",
        )
    return [_task_to_read(t) for t in sorted(plan.tasks, key=lambda t: t.sort_order)]


@router.post("/{plan_id}/tasks", response_model=MaintenanceTaskRead, status_code=status.HTTP_201_CREATED)
def create_maintenance_task(
    plan_id: UUID,
    payload: MaintenanceTaskCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MaintenanceTask:
    """Add task to maintenance plan."""
    plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wartungsplan nicht gefunden",
        )
    task = MaintenanceTask(
        maintenance_plan_id=plan_id,
        name=payload.name,
        description=payload.description,
        sort_order=payload.sort_order,
        article_id=payload.article_id,
        quantity=payload.quantity,
        unit=payload.unit,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _task_to_read(task)


@router.patch("/{plan_id}/tasks/{task_id}", response_model=MaintenanceTaskRead)
def update_maintenance_task(
    plan_id: UUID,
    task_id: UUID,
    payload: MaintenanceTaskUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MaintenanceTaskRead:
    """Wartungsaufgabe aktualisieren (z. B. Artikel zuweisen)."""
    task = (
        db.query(MaintenanceTask)
        .filter(
            MaintenanceTask.id == task_id,
            MaintenanceTask.maintenance_plan_id == plan_id,
        )
        .first()
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aufgabe nicht gefunden",
        )
    if payload.name is not None:
        task.name = payload.name
    if payload.description is not None:
        task.description = payload.description
    if payload.sort_order is not None:
        task.sort_order = payload.sort_order
    if payload.article_id is not None:
        task.article_id = payload.article_id
    else:
        # Explizit auf None setzen wenn article_id im Payload enthalten ist
        if "article_id" in payload.model_fields_set:
            task.article_id = None
    if payload.quantity is not None:
        task.quantity = payload.quantity
    if payload.unit is not None:
        task.unit = payload.unit
    db.commit()
    db.refresh(task)
    return _task_to_read(task)


@router.delete("/{plan_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_maintenance_task(
    plan_id: UUID,
    task_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Remove task from maintenance plan."""
    task = (
        db.query(MaintenanceTask)
        .filter(
            MaintenanceTask.id == task_id,
            MaintenanceTask.maintenance_plan_id == plan_id,
        )
        .first()
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aufgabe nicht gefunden",
        )
    db.delete(task)
    db.commit()


@router.post("/{plan_id}/document", response_model=MaintenancePlanRead)
async def upload_plan_document(
    plan_id: UUID,
    file: Annotated[UploadFile, File()],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MaintenancePlanRead:
    """Hersteller-Dokument (PDF) an Wartungsplan anhängen. Ersetzt ein vorhandenes Dokument."""
    plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wartungsplan nicht gefunden")

    if file.content_type not in ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dateityp nicht erlaubt. Erlaubt: PDF, JPEG, PNG",
        )

    content = await file.read()
    if len(content) > MAX_DOCUMENT_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Datei zu groß (max. 20 MB)")

    # Vorhandenes Dokument ersetzen
    if plan.document_id:
        old_doc = db.query(Document).filter(Document.id == plan.document_id).first()
        if old_doc:
            try:
                Path(old_doc.file_path).unlink(missing_ok=True)
            except OSError:
                pass
            db.delete(old_doc)
            db.flush()

    settings = get_settings()
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "document.pdf").suffix or ".pdf"
    stored_name = f"{uuid.uuid4()}{ext}"
    file_path = upload_dir / stored_name
    file_path.write_bytes(content)

    doc = Document(
        filename=file.filename or stored_name,
        content_type=file.content_type,
        file_path=str(file_path),
        file_size=len(content),
        created_by=current_user.id,
    )
    db.add(doc)
    db.flush()

    plan.document_id = doc.id
    db.commit()
    db.refresh(plan)
    return MaintenancePlanRead.from_orm_with_document(plan)


@router.delete("/{plan_id}/document", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan_document(
    plan_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Dokument vom Wartungsplan entfernen und Datei löschen."""
    plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wartungsplan nicht gefunden")
    if not plan.document_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kein Dokument vorhanden")

    doc = db.query(Document).filter(Document.id == plan.document_id).first()
    plan.document_id = None
    if doc:
        try:
            Path(doc.file_path).unlink(missing_ok=True)
        except OSError:
            pass
        db.delete(doc)
    db.commit()


@router.get("/{plan_id}/document")
def download_plan_document(
    plan_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FileResponse:
    """Hersteller-Dokument des Wartungsplans herunterladen."""
    plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == plan_id).first()
    if not plan or not plan.document_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kein Dokument vorhanden")

    doc = db.query(Document).filter(Document.id == plan.document_id).first()
    if not doc or not Path(doc.file_path).exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Datei nicht gefunden")

    return FileResponse(
        path=doc.file_path,
        media_type=doc.content_type,
        filename=doc.filename,
    )
