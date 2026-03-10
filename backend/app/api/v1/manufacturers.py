"""Manufacturers and VehicleModels API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.manufacturer import Manufacturer, VehicleModel
from app.models.user import User
from app.schemas.manufacturer import (
    ManufacturerCreate,
    ManufacturerRead,
    VehicleModelCreate,
    VehicleModelRead,
)

router = APIRouter(prefix="/manufacturers", tags=["manufacturers"])


@router.get("", response_model=list[ManufacturerRead])
def list_manufacturers(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[Manufacturer]:
    """List manufacturers."""
    return db.query(Manufacturer).order_by(Manufacturer.name).all()


@router.post("", response_model=ManufacturerRead, status_code=status.HTTP_201_CREATED)
def create_manufacturer(
    payload: ManufacturerCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Manufacturer:
    """Create manufacturer."""
    existing = db.query(Manufacturer).filter(
        Manufacturer.name == payload.name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hersteller existiert bereits",
        )
    manufacturer = Manufacturer(name=payload.name)
    db.add(manufacturer)
    db.commit()
    db.refresh(manufacturer)
    return manufacturer


@router.get("/{manufacturer_id}/models", response_model=list[VehicleModelRead])
def list_vehicle_models(
    manufacturer_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[VehicleModel]:
    """List vehicle models for manufacturer."""
    return (
        db.query(VehicleModel)
        .filter(VehicleModel.manufacturer_id == manufacturer_id)
        .order_by(VehicleModel.name)
        .all()
    )


@router.post("/models", response_model=VehicleModelRead, status_code=status.HTTP_201_CREATED)
def create_vehicle_model(
    payload: VehicleModelCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> VehicleModel:
    """Create vehicle model."""
    model = VehicleModel(
        manufacturer_id=payload.manufacturer_id,
        name=payload.name,
        variant=payload.variant,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model
