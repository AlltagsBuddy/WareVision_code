"""Inventur API: Bestandsaufnahme mit Zählliste, Differenzbuchung und Inventurliste."""

import csv
import io
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.article import Article
from app.models.article_category import ArticleCategory
from app.models.stock_count import StockCount, StockCountItem
from app.models.storage_location import StorageLocation
from app.models.user import User
from app.schemas.stock_count import (
    StockCountCreate,
    StockCountDetail,
    StockCountItemRead,
    StockCountItemUpdate,
    StockCountRead,
)
from app.services.audit import log_audit
from app.services.stock_booking import apply_stock_change

router = APIRouter(prefix="/stock-counts", tags=["stock-counts"])

_CENT = Decimal("0.01")


def _next_count_number(db: Session, year: int) -> str:
    """Nächste Inventurnummer (z. B. INV-2026-01)."""
    last = (
        db.query(StockCount)
        .filter(StockCount.count_number.like(f"INV-{year}-%"))
        .order_by(StockCount.count_number.desc())
        .first()
    )
    num = 1
    if last:
        try:
            num = int(last.count_number.split("-")[-1]) + 1
        except (IndexError, ValueError):
            pass
    return f"INV-{year}-{num:02d}"


def _get_count(db: Session, count_id: UUID) -> StockCount:
    """Inventur laden oder 404."""
    sc = db.query(StockCount).filter(StockCount.id == count_id).first()
    if not sc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventur nicht gefunden")
    return sc


def _to_read(sc: StockCount, with_items: bool = False) -> dict:
    """Inventur inkl. Fortschritt als Dict."""
    data = {
        "id": sc.id,
        "count_number": sc.count_number,
        "count_date": sc.count_date,
        "status": sc.status,
        "scope_label": sc.scope_label,
        "notes": sc.notes,
        "value_expected": sc.value_expected,
        "value_counted": sc.value_counted,
        "completed_at": sc.completed_at,
        "created_at": sc.created_at,
        "total_items": len(sc.items),
        "counted_items": sum(1 for i in sc.items if i.counted_qty is not None),
    }
    if with_items:
        data["items"] = [StockCountItemRead.model_validate(i) for i in sc.items]
    return data


@router.get("", response_model=list[StockCountRead])
def list_stock_counts(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[dict]:
    """Alle Inventuren (neueste zuerst)."""
    counts = db.query(StockCount).order_by(StockCount.count_date.desc(), StockCount.count_number.desc()).all()
    return [_to_read(sc) for sc in counts]


@router.post("", response_model=StockCountDetail, status_code=status.HTTP_201_CREATED)
def create_stock_count(
    payload: StockCountCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> dict:
    """Neue Inventur anlegen: alle aktiven Artikel im gewählten Umfang werden in die Zählliste übernommen."""
    if db.query(StockCount.id).filter(StockCount.status == "open").first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Es läuft bereits eine Inventur. Bitte diese zuerst abschließen oder abbrechen.",
        )

    q = db.query(Article).filter(Article.is_active.is_(True))
    scope: list[str] = []
    locations = {loc.id: loc.name for loc in db.query(StorageLocation).all()}
    if payload.storage_location_id:
        if payload.storage_location_id not in locations:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lagerort nicht gefunden")
        q = q.filter(Article.storage_location_id == payload.storage_location_id)
        scope.append(f"Lagerort: {locations[payload.storage_location_id]}")
    if payload.category_id:
        cat = db.query(ArticleCategory).filter(ArticleCategory.id == payload.category_id).first()
        if not cat:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kategorie nicht gefunden")
        q = q.filter(Article.category_id == payload.category_id)
        scope.append(f"Kategorie: {cat.name}")
    articles = q.all()
    if not articles:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Im gewählten Umfang gibt es keine aktiven Artikel")

    sc = StockCount(
        count_number=_next_count_number(db, payload.count_date.year),
        count_date=payload.count_date,
        status="open",
        storage_location_id=payload.storage_location_id,
        category_id=payload.category_id,
        scope_label=", ".join(scope) or "Gesamtes Lager",
        notes=(payload.notes or "").strip() or None,
        created_by=current_user.id,
    )
    for a in articles:
        loc_parts = [locations.get(a.storage_location_id) if a.storage_location_id else None, a.location_label]
        location = " / ".join(p for p in loc_parts if p) or None
        sc.items.append(StockCountItem(
            article_id=a.id,
            article_number=a.article_number,
            article_name=a.name,
            location=location,
            barcode=a.barcode,
            unit_cost=a.purchase_price or Decimal("0"),
            # Sortierung wie im Lager: Lagerort, dann Artikelnummer
            sort_key=f"{(location or '~').lower()}|{a.article_number.lower()}",
            book_qty_at_start=a.stock_quantity,
        ))
    db.add(sc)
    db.flush()
    log_audit(
        db, user_id=current_user.id, entity_type="stock_count", entity_id=sc.id, action="create",
        new_values={"count_number": sc.count_number, "items": len(articles), "scope": sc.scope_label},
    )
    db.commit()
    db.refresh(sc)
    return _to_read(sc, with_items=True)


@router.get("/{count_id}", response_model=StockCountDetail)
def get_stock_count(
    count_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Inventur mit allen Zählpositionen."""
    return _to_read(_get_count(db, count_id), with_items=True)


@router.put("/{count_id}/items/{item_id}", response_model=StockCountItemRead)
def update_count_item(
    count_id: UUID,
    item_id: UUID,
    payload: StockCountItemUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StockCountItem:
    """Ist-Menge erfassen. Der Soll-Bestand wird im Moment der Zählung festgehalten."""
    sc = _get_count(db, count_id)
    if sc.status != "open":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Die Inventur ist nicht mehr offen")
    item = (
        db.query(StockCountItem)
        .filter(StockCountItem.id == item_id, StockCountItem.stock_count_id == count_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zählposition nicht gefunden")

    if payload.counted_qty is None:
        item.counted_qty = None
        item.expected_qty = None
        item.counted_by = None
        item.counted_at = None
    else:
        article = db.query(Article).filter(Article.id == item.article_id).first()
        item.expected_qty = article.stock_quantity if article else item.book_qty_at_start
        item.counted_qty = payload.counted_qty
        item.counted_by = current_user.id
        item.counted_at = datetime.now(timezone.utc)
    if payload.note is not None:
        item.note = payload.note.strip() or None
    db.commit()
    db.refresh(item)
    return item


@router.post("/{count_id}/complete", response_model=StockCountDetail)
def complete_stock_count(
    count_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> dict:
    """Inventur abschließen: Differenzen als Lagerkorrektur buchen, danach unveränderbar (GoBD)."""
    sc = _get_count(db, count_id)
    if sc.status != "open":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Die Inventur ist nicht mehr offen")
    missing = [i for i in sc.items if i.counted_qty is None]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Noch {len(missing)} Artikel nicht gezählt (z. B. {missing[0].article_number}). "
            "Bitte alle Positionen zählen – auch Bestand 0 eintragen.",
        )

    value_expected = Decimal("0")
    value_counted = Decimal("0")
    try:
        for item in sc.items:
            diff = item.counted_qty - item.expected_qty
            item.difference = diff
            value_expected += item.unit_cost * item.expected_qty
            value_counted += item.unit_cost * item.counted_qty
            if diff == 0:
                continue
            apply_stock_change(
                db,
                article_id=item.article_id,
                quantity=abs(diff),
                movement_type="incoming" if diff > 0 else "correction",
                reference_type="stock_count",
                reference_id=item.id,
                notes=f"Inventur {sc.count_number}: {'Mehrbestand' if diff > 0 else 'Fehlbestand'} {abs(diff)}",
                user_id=current_user.id,
            )
    except HTTPException as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Abschluss nicht möglich: {exc.detail}. Bitte die betroffene Position neu zählen.",
        ) from exc

    sc.value_expected = value_expected.quantize(_CENT)
    sc.value_counted = value_counted.quantize(_CENT)
    sc.status = "completed"
    sc.completed_by = current_user.id
    sc.completed_at = datetime.now(timezone.utc)
    log_audit(
        db, user_id=current_user.id, entity_type="stock_count", entity_id=sc.id, action="complete",
        new_values={
            "count_number": sc.count_number,
            "differences": sum(1 for i in sc.items if i.difference),
            "value_expected": str(sc.value_expected),
            "value_counted": str(sc.value_counted),
        },
    )
    db.commit()
    db.refresh(sc)
    return _to_read(sc, with_items=True)


@router.post("/{count_id}/cancel", response_model=StockCountRead)
def cancel_stock_count(
    count_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> dict:
    """Offene Inventur abbrechen (keine Lagerbuchung). Die Zählung bleibt zur Nachvollziehbarkeit erhalten."""
    sc = _get_count(db, count_id)
    if sc.status != "open":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nur offene Inventuren können abgebrochen werden")
    sc.status = "cancelled"
    log_audit(db, user_id=current_user.id, entity_type="stock_count", entity_id=sc.id, action="cancel",
              new_values={"count_number": sc.count_number})
    db.commit()
    db.refresh(sc)
    return _to_read(sc)


@router.get("/{count_id}/pdf")
def get_stock_count_pdf(
    count_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Offen: Zählliste zum Ausdrucken. Abgeschlossen: Inventurliste mit Lagerwert."""
    from app.services.stock_count_pdf import generate_stock_count_pdf

    sc = _get_count(db, count_id)
    kind = "Inventurliste" if sc.status == "completed" else "Zaehlliste"
    return Response(
        content=generate_stock_count_pdf(db, sc),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{kind}_{sc.count_number}.pdf"'},
    )


@router.get("/{count_id}/csv")
def get_stock_count_csv(
    count_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Inventurliste als CSV (Semikolon, deutsches Zahlenformat) für den Steuerberater."""
    sc = _get_count(db, count_id)

    def num(v: Decimal | int | None) -> str:
        return "" if v is None else str(v).replace(".", ",")

    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow([f"Inventur {sc.count_number}", f"Stichtag {sc.count_date.strftime('%d.%m.%Y')}", sc.scope_label or ""])
    w.writerow(["Artikelnr.", "Bezeichnung", "Lagerort", "Soll", "Ist", "Differenz", "EK netto (EUR)", "Wert Ist (EUR)", "Bemerkung"])
    for i in sc.items:
        value = (i.unit_cost * i.counted_qty).quantize(_CENT) if i.counted_qty is not None else None
        diff = i.difference if i.difference is not None else (
            i.counted_qty - i.expected_qty if i.counted_qty is not None and i.expected_qty is not None else None
        )
        w.writerow([i.article_number, i.article_name, i.location or "", num(i.expected_qty), num(i.counted_qty),
                    num(diff), num(i.unit_cost), num(value), i.note or ""])
    if sc.value_counted is not None:
        w.writerow([])
        w.writerow(["", "Lagerwert laut Buchbestand", "", "", "", "", "", num(sc.value_expected), ""])
        w.writerow(["", "Lagerwert laut Inventur", "", "", "", "", "", num(sc.value_counted), ""])
    return Response(
        content=buf.getvalue().encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="Inventur_{sc.count_number}.csv"'},
    )
