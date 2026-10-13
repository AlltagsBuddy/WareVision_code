"""Artikelkategorien API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.article_category import ArticleCategory
from app.models.user import User
from app.schemas.article_category import (
    ArticleCategoryCreate,
    ArticleCategoryRead,
    ArticleCategoryUpdate,
)

router = APIRouter(prefix="/article-categories", tags=["article-categories"])


@router.get("", response_model=list[ArticleCategoryRead])
def list_article_categories(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ArticleCategory]:
    """Alle Artikelkategorien auflisten."""
    return db.query(ArticleCategory).order_by(ArticleCategory.name).all()


@router.post("", response_model=ArticleCategoryRead, status_code=status.HTTP_201_CREATED)
def create_article_category(
    payload: ArticleCategoryCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> ArticleCategory:
    """Neue Artikelkategorie anlegen."""
    existing = db.query(ArticleCategory).filter(ArticleCategory.name == payload.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Eine Kategorie mit diesem Namen existiert bereits",
        )
    category = ArticleCategory(name=payload.name, description=payload.description)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.patch("/{category_id}", response_model=ArticleCategoryRead)
def update_article_category(
    category_id: UUID,
    payload: ArticleCategoryUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> ArticleCategory:
    """Artikelkategorie aktualisieren."""
    category = db.query(ArticleCategory).filter(ArticleCategory.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kategorie nicht gefunden",
        )
    if payload.name is not None:
        existing = (
            db.query(ArticleCategory)
            .filter(ArticleCategory.name == payload.name, ArticleCategory.id != category_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Eine Kategorie mit diesem Namen existiert bereits",
            )
        category.name = payload.name
    if payload.description is not None:
        category.description = payload.description
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article_category(
    category_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> None:
    """Artikelkategorie löschen. Artikel dieser Kategorie werden nicht gelöscht."""
    category = db.query(ArticleCategory).filter(ArticleCategory.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kategorie nicht gefunden",
        )
    db.delete(category)
    db.commit()
