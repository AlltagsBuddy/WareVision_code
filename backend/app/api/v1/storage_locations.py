"""Lagerorte API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_right
from app.core.database import get_db
from app.models.article import Article
from app.models.storage_location import StorageLocation
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.storage_location import (
    StorageLocationCreate,
    StorageLocationRead,
    StorageLocationUpdate,
)

router = APIRouter(prefix="/storage-locations", tags=["storage-locations"])


@router.get("", response_model=list[StorageLocationRead])
def list_storage_locations(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    include_inactive: bool = False,
) -> list[StorageLocation]:
    """Alle Lagerorte auflisten."""
    query = db.query(StorageLocation)
    if not include_inactive:
        query = query.filter(StorageLocation.is_active == True)
    return query.order_by(StorageLocation.name).all()


@router.post("", response_model=StorageLocationRead, status_code=status.HTTP_201_CREATED)
def create_storage_location(
    payload: StorageLocationCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_right("lager_einkauf"))],
) -> StorageLocation:
    """Neuen Lagerort anlegen."""
    existing = db.query(StorageLocation).filter(StorageLocation.name == payload.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ein Lagerort mit diesem Namen existiert bereits",
        )
    location = StorageLocation(name=payload.name, description=payload.description)
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


@router.patch("/{location_id}", response_model=StorageLocationRead)
def update_storage_location(
    location_id: UUID,
    payload: StorageLocationUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_right("lager_einkauf"))],
) -> StorageLocation:
    """Lagerort aktualisieren."""
    location = db.query(StorageLocation).filter(StorageLocation.id == location_id).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lagerort nicht gefunden",
        )
    if payload.name is not None:
        existing = (
            db.query(StorageLocation)
            .filter(StorageLocation.name == payload.name, StorageLocation.id != location_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ein Lagerort mit diesem Namen existiert bereits",
            )
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(location, key, value)
    db.commit()
    db.refresh(location)
    return location


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_storage_location(
    location_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_right("lager_einkauf"))],
) -> None:
    """Lagerort löschen. Schlägt fehl wenn noch Artikel oder Fahrzeuge zugewiesen sind."""
    location = db.query(StorageLocation).filter(StorageLocation.id == location_id).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lagerort nicht gefunden",
        )
    article_count = db.query(Article).filter(Article.storage_location_id == location_id).count()
    vehicle_count = db.query(Vehicle).filter(Vehicle.storage_location_id == location_id).count()
    if article_count > 0 or vehicle_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Lagerort kann nicht gelöscht werden: {article_count} Artikel und {vehicle_count} Fahrzeuge sind noch zugewiesen",
        )
    db.delete(location)
    db.commit()
