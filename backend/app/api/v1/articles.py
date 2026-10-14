"""Articles API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.article import Article
from app.models.manufacturer import VehicleModel
from app.models.user import User
from app.schemas.article import ArticleCreate, ArticleRead, ArticleUpdate

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("", response_model=list[ArticleRead])
def list_articles(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: str | None = None,
    barcode: str | None = None,
    category_id: UUID | None = None,
) -> list[ArticleRead]:
    """Artikel auflisten. barcode für Scanner-Lookup, category_id für Kategoriefilter."""
    query = db.query(Article).filter(Article.is_active == True)
    if barcode:
        query = query.filter(Article.barcode == barcode)
    else:
        if search:
            query = query.filter(
                Article.article_number.ilike(f"%{search}%")
                | Article.name.ilike(f"%{search}%")
            )
        if category_id:
            query = query.filter(Article.category_id == category_id)
    articles = query.order_by(Article.name).offset(skip).limit(limit).all()
    return [ArticleRead.from_orm_with_models(a) for a in articles]


@router.post("", response_model=ArticleRead, status_code=status.HTTP_201_CREATED)
def create_article(
    payload: ArticleCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ArticleRead:
    """Create article."""
    existing = db.query(Article).filter(
        Article.article_number == payload.article_number
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Artikel mit dieser Artikelnummer existiert bereits",
        )
    article = Article(
        article_number=payload.article_number,
        name=payload.name,
        description=payload.description,
        category_id=payload.category_id,
        supplier_id=payload.supplier_id,
        purchase_price=payload.purchase_price,
        sales_price_b2c=payload.sales_price_b2c,
        sales_price_b2b=payload.sales_price_b2b,
        vat_rate=payload.vat_rate,
        minimum_stock=payload.minimum_stock,
        target_stock=payload.target_stock,
        supplier_article_number=(payload.supplier_article_number or "").strip() or None,
        barcode=payload.barcode,
        qr_code=payload.qr_code,
        oem_number=payload.oem_number,
        location_label=payload.location_label,
        storage_location_id=payload.storage_location_id,
    )
    # Kompatible Fahrzeugmodelle verknüpfen
    if payload.compatible_model_ids:
        models = db.query(VehicleModel).filter(
            VehicleModel.id.in_(payload.compatible_model_ids)
        ).all()
        article.compatible_models = models
    db.add(article)
    db.commit()
    db.refresh(article)
    return ArticleRead.from_orm_with_models(article)


@router.get("/{article_id}", response_model=ArticleRead)
def get_article(
    article_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ArticleRead:
    """Get article by ID."""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artikel nicht gefunden",
        )
    return ArticleRead.from_orm_with_models(article)


@router.get("/barcode/{barcode}", response_model=ArticleRead)
def get_article_by_barcode(
    barcode: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ArticleRead:
    """Get article by barcode (for QR/Barcode scan)."""
    article = db.query(Article).filter(Article.barcode == barcode).first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artikel mit diesem Barcode nicht gefunden",
        )
    return ArticleRead.from_orm_with_models(article)


@router.patch("/{article_id}", response_model=ArticleRead)
def update_article(
    article_id: UUID,
    payload: ArticleUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ArticleRead:
    """Update article."""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artikel nicht gefunden",
        )
    data = payload.model_dump(exclude_unset=True)
    # compatible_model_ids separat behandeln (Relationship, kein direktes Feld)
    compatible_model_ids = data.pop("compatible_model_ids", None)
    for key, value in data.items():
        setattr(article, key, value)
    if compatible_model_ids is not None:
        models = db.query(VehicleModel).filter(
            VehicleModel.id.in_(compatible_model_ids)
        ).all()
        article.compatible_models = models
    db.commit()
    db.refresh(article)
    return ArticleRead.from_orm_with_models(article)


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(
    article_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> None:
    """Soft delete article (deactivate)."""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artikel nicht gefunden",
        )
    article.is_active = False
    db.commit()
