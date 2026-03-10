"""Stock movements API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.article import Article
from app.models.stock_movement import StockMovement
from app.models.user import User
from app.schemas.stock import StockMovementCreate, StockMovementRead

router = APIRouter(prefix="/stock", tags=["stock"])


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

    new_stock = article.stock_quantity + delta
    if new_stock < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nicht genug Bestand. Aktuell: {article.stock_quantity}",
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
    return [
        {
            "id": str(a.id),
            "article_number": a.article_number,
            "name": a.name,
            "stock_quantity": a.stock_quantity,
            "minimum_stock": a.minimum_stock,
        }
        for a in articles
    ]
