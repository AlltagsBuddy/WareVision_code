"""Stundenpreise API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.labor_rate import LaborRate
from app.models.user import User
from app.schemas.labor_rate import LaborRateCreate, LaborRateRead, LaborRateUpdate

router = APIRouter(prefix="/labor-rates", tags=["labor-rates"])


@router.get("", response_model=list[LaborRateRead])
def list_labor_rates(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[LaborRate]:
    """Alle Stundenpreise auflisten."""
    return db.query(LaborRate).order_by(LaborRate.is_default.desc(), LaborRate.name).all()


@router.post("", response_model=LaborRateRead, status_code=status.HTTP_201_CREATED)
def create_labor_rate(
    payload: LaborRateCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> LaborRate:
    """Neuen Stundenpreis anlegen."""
    if payload.is_default:
        db.query(LaborRate).update({"is_default": False})
    rate = LaborRate(
        name=payload.name,
        description=payload.description,
        rate_per_hour=payload.rate_per_hour,
        is_default=payload.is_default,
    )
    db.add(rate)
    db.commit()
    db.refresh(rate)
    return rate


@router.patch("/{rate_id}", response_model=LaborRateRead)
def update_labor_rate(
    rate_id: UUID,
    payload: LaborRateUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> LaborRate:
    """Stundenpreis aktualisieren."""
    rate = db.query(LaborRate).filter(LaborRate.id == rate_id).first()
    if not rate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stundenpreis nicht gefunden")
    if payload.name is not None:
        rate.name = payload.name
    if payload.description is not None:
        rate.description = payload.description
    if payload.rate_per_hour is not None:
        rate.rate_per_hour = payload.rate_per_hour
    if payload.is_active is not None:
        rate.is_active = payload.is_active
    if payload.is_default is True:
        db.query(LaborRate).filter(LaborRate.id != rate_id).update({"is_default": False})
        rate.is_default = True
    elif payload.is_default is False:
        rate.is_default = False
    db.commit()
    db.refresh(rate)
    return rate


@router.delete("/{rate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_labor_rate(
    rate_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> None:
    """Stundenpreis löschen."""
    rate = db.query(LaborRate).filter(LaborRate.id == rate_id).first()
    if not rate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stundenpreis nicht gefunden")
    db.delete(rate)
    db.commit()
