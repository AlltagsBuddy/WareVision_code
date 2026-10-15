"""Lieferanten-Artikeldaten (Katalog): Import, Nachschlagen per Barcode, Etikett-Foto mit KI."""

import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, module_guard, require_right
from app.core.database import get_db
from app.models.app_setting import AppSetting
from app.models.supplier import Supplier
from app.models.supplier_catalog import SupplierCatalogItem
from app.models.user import User
from app.services import label_recognition
from app.services import supplier_catalog as catalog
from app.services.audit import log_audit

router = APIRouter(prefix="/article-catalog", tags=["article-catalog"],
                   dependencies=[Depends(module_guard("articles"))])

PREVIEW_ROWS = 5


def _item(i: SupplierCatalogItem) -> dict:
    return {
        "id": str(i.id),
        "supplier_id": str(i.supplier_id) if i.supplier_id else None,
        "supplier_name": i.supplier_name,
        "source": i.source,
        "source_ref": i.source_ref,
        "barcode": i.barcode,
        "supplier_article_number": i.supplier_article_number,
        "name": i.name,
        "description": i.description,
        "manufacturer": i.manufacturer,
        "manufacturer_part_number": i.manufacturer_part_number,
        "purchase_price": float(i.purchase_price) if i.purchase_price is not None else None,
        "retail_price_net": float(i.retail_price_net) if i.retail_price_net is not None else None,
        "vat_rate": float(i.vat_rate) if i.vat_rate is not None else None,
        "unit": i.unit,
        "updated_at": i.updated_at.isoformat() if i.updated_at else None,
    }


@router.get("/lookup")
def lookup(
    barcode: Annotated[str, Query(min_length=1, max_length=255)],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[dict]:
    """Vorschläge zu einem gescannten Barcode (aus Artikeldateien und E-Rechnungen)."""
    return [_item(i) for i in catalog.lookup_barcode(db, barcode)]


@router.get("/search")
def search(
    q: Annotated[str, Query(min_length=2, max_length=100)],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[dict]:
    """Suche nach Bezeichnung, Bestellnummer, Herstellernummer oder Barcode."""
    return [_item(i) for i in catalog.search(db, q)]


@router.get("/sources")
def sources(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[dict]:
    """Übersicht: welche Lieferantendaten vorhanden sind."""
    rows = (db.query(SupplierCatalogItem.supplier_name, SupplierCatalogItem.source,
                     func.count(SupplierCatalogItem.id), func.max(SupplierCatalogItem.updated_at))
            .group_by(SupplierCatalogItem.supplier_name, SupplierCatalogItem.source)
            .order_by(SupplierCatalogItem.supplier_name).all())
    return [{"supplier_name": n, "source": s, "count": c, "updated_at": u.isoformat() if u else None}
            for n, s, c, u in rows]


@router.post("/import/preview")
async def import_preview(
    file: Annotated[UploadFile, File(...)],
    current_user: Annotated[User, Depends(require_right("lager_einkauf"))],
) -> dict:
    """Datei lesen: Spaltenüberschriften, erste Zeilen und vorgeschlagene Zuordnung."""
    content = await file.read()
    try:
        table = catalog.read_table(content, file.filename or "")
    except catalog.CatalogError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return {
        "headers": table.headers,
        "sample": table.rows[:PREVIEW_ROWS],
        "row_count": len(table.rows),
        "mapping": catalog.suggest_mapping(table.headers),
        "fields": [{"key": k, "label": v[0]} for k, v in catalog.FIELDS.items()],
    }


@router.post("/import")
async def import_file(
    file: Annotated[UploadFile, File(...)],
    mapping: Annotated[str, Form(...)],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_right("lager_einkauf"))],
    supplier_id: Annotated[str | None, Form()] = None,
    supplier_name: Annotated[str | None, Form()] = None,
) -> dict:
    """Artikeldatei eines Lieferanten speichern (vorhandene Einträge werden aktualisiert)."""
    supplier = None
    if supplier_id:
        try:
            supplier = db.query(Supplier).filter(Supplier.id == UUID(supplier_id)).first()
        except ValueError:
            supplier = None
        if not supplier:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lieferant nicht gefunden")
    name = (supplier.name if supplier else (supplier_name or "")).strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bitte den Lieferanten angeben.")
    try:
        raw = json.loads(mapping)
        cols = {k: (int(v) if v is not None and str(v) != "" else None) for k, v in raw.items() if k in catalog.FIELDS}
    except (ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ungültige Spaltenzuordnung") from exc
    content = await file.read()
    try:
        table = catalog.read_table(content, file.filename or "")
        res = catalog.import_table(db, table, cols, name[:255], supplier.id if supplier else None,
                                   (file.filename or "Datei")[:255])
    except catalog.CatalogError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    log_audit(db, user_id=current_user.id, entity_type="article_catalog", entity_id=None, action="catalog_import",
              new_values={"supplier": name, "file": file.filename, "created": res.created,
                          "updated": res.updated, "skipped": res.skipped})
    db.commit()
    return {"supplier_name": name, "created": res.created, "updated": res.updated, "skipped": res.skipped}


@router.delete("")
def delete_supplier_data(
    supplier_name: Annotated[str, Query(min_length=1)],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_right("lager_einkauf"))],
) -> dict:
    """Alle Artikeldaten eines Lieferanten entfernen (Lagerartikel bleiben unverändert)."""
    n = db.query(SupplierCatalogItem).filter(SupplierCatalogItem.supplier_name == supplier_name).delete()
    log_audit(db, user_id=current_user.id, entity_type="article_catalog", entity_id=None, action="catalog_delete",
              new_values={"supplier": supplier_name, "deleted": n})
    db.commit()
    return {"deleted": n}


def _ai_key(db: Session) -> tuple[str | None, str | None]:
    rows = db.query(AppSetting).filter(AppSetting.key.in_(("ai_help_api_key", "ai_help_model"))).all()
    values = {r.key: (r.value or "").strip() for r in rows}
    return values.get("ai_help_api_key") or None, values.get("ai_help_model") or None


@router.get("/recognize-label/status")
def recognize_status(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Ist die KI für die Etikett-Erkennung eingerichtet?"""
    return {"enabled": bool(_ai_key(db)[0])}


@router.post("/recognize-label")
async def recognize_label(
    file: Annotated[UploadFile, File(...)],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Etikett-Foto mit KI auslesen. Liefert nur Vorschläge; das Foto wird nicht gespeichert."""
    api_key, model = _ai_key(db)
    if not api_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Die KI ist nicht eingerichtet (Einstellungen → KI-Hilfe: API-Key).")
    content = await file.read()
    try:
        result = label_recognition.recognize(content, api_key, model)
    except label_recognition.LabelError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    matches = catalog.lookup_barcode(db, result["barcode"]) if result.get("barcode") else []
    return {"suggestion": result, "catalog": [_item(i) for i in matches]}
