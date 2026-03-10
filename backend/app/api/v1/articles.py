"""Articles API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.article import Article
from app.models.user import User
from app.schemas.article import ArticleCreate, ArticleRead, ArticleUpdate

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("", response_model=list[ArticleRead])
def list_articles(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: str | None = None,
    barcode: str | None = None,
) -> list[Article]:
    """List articles. Use barcode for scan lookup."""
    query = db.query(Article).filter(Article.is_active == True)
    if barcode:
        query = query.filter(Article.barcode == barcode)
    elif search:
        query = query.filter(
            Article.article_number.ilike(f"%{search}%")
            | Article.name.ilike(f"%{search}%")
        )
    return query.offset(skip).limit(limit).all()


@router.post("", response_model=ArticleRead, status_code=status.HTTP_201_CREATED)
def create_article(
    payload: ArticleCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Article:
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
        barcode=payload.barcode,
        qr_code=payload.qr_code,
        oem_number=payload.oem_number,
        location_label=payload.location_label,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


@router.get("/{article_id}", response_model=ArticleRead)
def get_article(
    article_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Article:
    """Get article by ID."""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artikel nicht gefunden",
        )
    return article


@router.get("/barcode/{barcode}", response_model=ArticleRead)
def get_article_by_barcode(
    barcode: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Article:
    """Get article by barcode (for QR/Barcode scan)."""
    article = db.query(Article).filter(Article.barcode == barcode).first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artikel mit diesem Barcode nicht gefunden",
        )
    return article


@router.patch("/{article_id}", response_model=ArticleRead)
def update_article(
    article_id: UUID,
    payload: ArticleUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Article:
    """Update article."""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artikel nicht gefunden",
        )
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(article, key, value)
    db.commit()
    db.refresh(article)
    return article


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(
    article_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
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
