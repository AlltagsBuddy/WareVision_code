"""Stock movements and reservations API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.article import Article
from app.models.stock_movement import StockMovement
from app.models.stock_reservation import StockReservation
from app.models.user import User
from app.schemas.stock import (
    StockMovementCreate,
    StockMovementRead,
    StockReservationCreate,
    StockReservationRead,
    StockReservationStatusUpdate,
)

router = APIRouter(prefix="/stock", tags=["stock"])


def _get_reserved_quantity(db: Session, article_id: UUID) -> int:
    """Sum of active reservations for article."""
    result = (
        db.query(func.coalesce(func.sum(StockReservation.quantity), 0))
        .filter(
            StockReservation.article_id == article_id,
            StockReservation.status == "active",
        )
        .scalar()
    )
    return int(result) if result else 0


@router.get("/movements", response_model=list[StockMovementRead])
def list_stock_movements(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    article_id: UUID | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[StockMovement]:
    """List stock movements."""
    query = db.query(StockMovement)
    if article_id:
        query = query.filter(StockMovement.article_id == article_id)
    return query.order_by(StockMovement.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/movements", response_model=StockMovementRead, status_code=status.HTTP_201_CREATED)
def create_stock_movement(
    payload: StockMovementCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StockMovement:
    """Create stock movement (Wareneingang, Warenausgang, Korrektur)."""
    article = db.query(Article).filter(Article.id == payload.article_id).first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artikel nicht gefunden",
        )

    # Quantity sign: incoming = positive, outgoing = negative
    sign = 1 if payload.movement_type == "incoming" else -1
    delta = sign * payload.quantity

    reserved = _get_reserved_quantity(db, payload.article_id)
    available = article.stock_quantity - reserved

    new_stock = article.stock_quantity + delta
    if new_stock < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nicht genug Bestand. Aktuell: {article.stock_quantity}",
        )
    if sign < 0 and available < payload.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nicht genug verfügbarer Bestand. Verfügbar: {available} (reserviert: {reserved})",
        )

    movement = StockMovement(
        article_id=payload.article_id,
        movement_type=payload.movement_type,
        quantity=payload.quantity,
        reference_type=payload.reference_type,
        reference_id=payload.reference_id,
        notes=payload.notes,
        created_by=current_user.id,
    )
    db.add(movement)
    article.stock_quantity = new_stock
    db.commit()
    db.refresh(movement)
    return movement


@router.get("/low-stock", response_model=list[dict])
def list_low_stock(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[dict]:
    """List articles below minimum stock (Mindestbestand Warnung)."""
    articles = (
        db.query(Article)
        .filter(
            Article.is_active == True,
            Article.minimum_stock > 0,
            Article.stock_quantity < Article.minimum_stock,
        )
        .all()
    )
    result = []
    for a in articles:
        reserved = _get_reserved_quantity(db, a.id)
        result.append({
            "id": str(a.id),
            "article_number": a.article_number,
            "name": a.name,
            "stock_quantity": a.stock_quantity,
            "reserved_quantity": reserved,
            "available_quantity": a.stock_quantity - reserved,
            "minimum_stock": a.minimum_stock,
        })
    return result


# --- Stock Reservations ---


@router.get("/reservations", response_model=list[StockReservationRead])
def list_reservations(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    article_id: UUID | None = None,
    status_filter: str | None = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[StockReservation]:
    """List stock reservations."""
    query = db.query(StockReservation)
    if article_id:
        query = query.filter(StockReservation.article_id == article_id)
    if status_filter:
        query = query.filter(StockReservation.status == status_filter)
    return query.order_by(StockReservation.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/reservations", response_model=StockReservationRead, status_code=status.HTTP_201_CREATED)
def create_reservation(
    payload: StockReservationCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StockReservation:
    """Create stock reservation."""
    article = db.query(Article).filter(Article.id == payload.article_id).first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artikel nicht gefunden",
        )
    reserved = _get_reserved_quantity(db, payload.article_id)
    available = article.stock_quantity - reserved
    if available < payload.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nicht genug verfügbarer Bestand. Verfügbar: {available} (reserviert: {reserved})",
        )
    reservation = StockReservation(
        article_id=payload.article_id,
        quantity=payload.quantity,
        reference_type=payload.reference_type,
        reference_id=payload.reference_id,
        notes=payload.notes,
        created_by=current_user.id,
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return reservation


@router.patch("/reservations/{reservation_id}", response_model=StockReservationRead)
def update_reservation_status(
    reservation_id: UUID,
    payload: StockReservationStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StockReservation:
    """Set reservation status to consumed or cancelled."""
    if payload.status not in ("consumed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status muss 'consumed' oder 'cancelled' sein",
        )
    reservation = db.query(StockReservation).filter(StockReservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservierung nicht gefunden",
        )
    if reservation.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Reservierung hat bereits Status '{reservation.status}'",
        )
    reservation.status = payload.status
    db.commit()
    db.refresh(reservation)
    return reservation
