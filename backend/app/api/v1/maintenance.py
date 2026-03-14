"""Maintenance plans API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.maintenance_plan import MaintenancePlan, MaintenanceTask
from app.models.user import User
from app.schemas.maintenance import (
    MaintenancePlanCreate,
    MaintenancePlanRead,
    MaintenanceTaskCreate,
    MaintenanceTaskRead,
)

router = APIRouter(prefix="/maintenance-plans", tags=["maintenance-plans"])


@router.get("", response_model=list[MaintenancePlanRead])
def list_maintenance_plans(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    manufacturer_id: UUID | None = None,
    vehicle_model_id: UUID | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[MaintenancePlan]:
    """List maintenance plans."""
    query = db.query(MaintenancePlan)
    if manufacturer_id:
        query = query.filter(MaintenancePlan.manufacturer_id == manufacturer_id)
    if vehicle_model_id:
        query = query.filter(MaintenancePlan.vehicle_model_id == vehicle_model_id)
    return query.order_by(MaintenancePlan.name).offset(skip).limit(limit).all()


@router.post("", response_model=MaintenancePlanRead, status_code=status.HTTP_201_CREATED)
def create_maintenance_plan(
    payload: MaintenancePlanCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MaintenancePlan:
    """Create maintenance plan."""
    plan = MaintenancePlan(
        manufacturer_id=payload.manufacturer_id,
        vehicle_model_id=payload.vehicle_model_id,
        name=payload.name,
        description=payload.description,
        interval_km=payload.interval_km,
        interval_hours=payload.interval_hours,
        interval_months=payload.interval_months,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/{plan_id}", response_model=MaintenancePlanRead)
def get_maintenance_plan(
    plan_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MaintenancePlan:
    """Get maintenance plan by ID."""
    plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wartungsplan nicht gefunden",
        )
    return plan


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


@router.get("/{plan_id}/tasks", response_model=list[MaintenanceTaskRead])
def list_maintenance_tasks(
    plan_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[MaintenanceTask]:
    """List tasks of a maintenance plan."""
    plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wartungsplan nicht gefunden",
        )
    return list(sorted(plan.tasks, key=lambda t: t.sort_order))


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
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


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
