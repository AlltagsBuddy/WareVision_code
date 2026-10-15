"""Articles API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, module_guard, require_right
from app.core.database import get_db
from app.models.article import Article
from app.models.manufacturer import VehicleModel
from app.models.user import User
from app.schemas.article import ArticleCreate, ArticleRead, ArticleUpdate

router = APIRouter(prefix="/articles", tags=["articles"], dependencies=[Depends(module_guard("articles"))])



def clean_barcode(code: str | None) -> str | None:
    """Barcode vereinheitlichen: Leerzeichen entfernen; leer → None."""
    if code is None:
        return None
    code = "".join(code.split())
    return code or None


def barcode_variants(code: str) -> list[str]:
    """Gleiche Ware kann als UPC-A (12 Ziffern) oder EAN-13 mit führender 0 gescannt werden."""
    code = clean_barcode(code) or ""
    variants = {code}
    if code.isdigit():
        if len(code) == 12:
            variants.add("0" + code)
        if len(code) == 13 and code.startswith("0"):
            variants.add(code[1:])
    return [v for v in variants if v]


def find_by_barcode(db: Session, code: str, exclude_id=None) -> Article | None:
    """Aktiven Artikel zu einem Barcode finden (inkl. EAN/UPC-Varianten)."""
    q = db.query(Article).filter(Article.is_active.is_(True), Article.barcode.in_(barcode_variants(code)))
    if exclude_id is not None:
        q = q.filter(Article.id != exclude_id)
    return q.order_by(Article.article_number).first()


def _ensure_barcode_free(db: Session, code: str | None, exclude_id=None) -> None:
    if not code:
        return
    other = find_by_barcode(db, code, exclude_id)
    if other:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Barcode {code} gehört schon zu Artikel {other.article_number} – {other.name}.",
        )


@router.get("", response_model=list[ArticleRead])
def list_articles(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: str | None = None,
    barcode: str | None = None,
    category_id: UUID | None = None,
    vehicle_model_id: UUID | None = None,
) -> list[ArticleRead]:
    """Artikel auflisten. barcode für Scanner-Lookup, category_id für Kategoriefilter,
    vehicle_model_id = nur Artikel, die zu diesem Fahrzeugmodell passen."""
    query = db.query(Article).filter(Article.is_active == True)
    if barcode:
        query = query.filter(Article.barcode.in_(barcode_variants(barcode)))
    else:
        if search:
            term = f"%{search}%"
            query = query.filter(
                Article.article_number.ilike(term)
                | Article.name.ilike(term)
                | Article.oem_number.ilike(term)
                | Article.supplier_article_number.ilike(term)
                | Article.part_manufacturer.ilike(term)
            )
        if category_id:
            query = query.filter(Article.category_id == category_id)
        if vehicle_model_id:
            query = query.filter(Article.compatible_models.any(VehicleModel.id == vehicle_model_id))
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
    barcode = clean_barcode(payload.barcode)
    _ensure_barcode_free(db, barcode)
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
        barcode=barcode,
        qr_code=payload.qr_code,
        oem_number=payload.oem_number,
        part_manufacturer=(payload.part_manufacturer or None),
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
    article = find_by_barcode(db, barcode)
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
    if "barcode" in data:
        data["barcode"] = clean_barcode(data["barcode"])
        if data["barcode"] != article.barcode:  # bestehende Doppelte nicht blockieren, nur neue verhindern
            _ensure_barcode_free(db, data["barcode"], exclude_id=article.id)
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


class BarcodeAssign(BaseModel):
    barcode: str = Field(..., min_length=1, max_length=255)
    replace: bool = False


@router.post("/{article_id}/barcode", response_model=ArticleRead)
def assign_barcode(
    article_id: UUID,
    payload: BarcodeAssign,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ArticleRead:
    """Gescannten Barcode einem Artikel zuordnen, damit er beim nächsten Scan erkannt wird."""
    from app.services.audit import log_audit

    article = db.query(Article).filter(Article.id == article_id, Article.is_active.is_(True)).first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artikel nicht gefunden")
    code = clean_barcode(payload.barcode)
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Barcode fehlt")
    if article.barcode and code in barcode_variants(article.barcode):
        return ArticleRead.from_orm_with_models(article)
    _ensure_barcode_free(db, code, exclude_id=article.id)
    if article.barcode and not payload.replace:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Artikel {article.article_number} hat schon den Barcode {article.barcode}. Ersetzen?",
        )
    old = article.barcode
    article.barcode = code
    db.flush()
    log_audit(db, user_id=current_user.id, entity_type="article", entity_id=article.id, action="barcode_assign",
              old_values={"barcode": old}, new_values={"barcode": code})
    db.commit()
    db.refresh(article)
    return ArticleRead.from_orm_with_models(article)


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(
    article_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_right("lager_einkauf"))],
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
