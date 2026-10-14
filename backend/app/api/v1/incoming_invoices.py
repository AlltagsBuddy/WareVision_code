"""Eingangsrechnungen API."""

import hashlib
import os
import uuid
from datetime import date
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.config import get_settings
from app.core.database import get_db
from app.models.incoming_invoice import IncomingInvoice
from app.models.user import User
from app.schemas.incoming_invoice import IncomingInvoiceCreate, IncomingInvoiceRead, IncomingInvoiceUpdate
from app.services.audit import log_audit
from app.services.einvoice_import import EInvoiceError, FORMAT_ZUGFERD, parse_einvoice

router = APIRouter(prefix="/incoming-invoices", tags=["incoming-invoices"])

_ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png"}
_MAX_SIZE = 20 * 1024 * 1024  # 20 MB
# Bei importierten E-Rechnungen dürfen nur diese Felder geändert werden (Original bleibt maßgeblich)
_EINVOICE_EDITABLE_FIELDS = {"status", "category", "notes"}


def _upload_dir() -> Path:
    """Upload-Verzeichnis für Eingangsrechnungs-PDFs."""
    path = Path(get_settings().UPLOAD_DIR) / "incoming_invoices"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _einvoice_dir() -> Path:
    """Archiv-Verzeichnis für unveränderte E-Rechnungs-Originale (GoBD)."""
    path = _upload_dir() / "einvoice_originals"
    path.mkdir(parents=True, exist_ok=True)
    return path


@router.get("", response_model=list[IncomingInvoiceRead])
def list_incoming_invoices(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    date_from: date | None = None,
    date_to: date | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> list[IncomingInvoice]:
    """Eingangsrechnungen auflisten. search: Lieferant oder Rechnungsnummer."""
    q = db.query(IncomingInvoice)
    if search and search.strip():
        term = f"%{search.strip()}%"
        q = q.filter(IncomingInvoice.supplier_name.ilike(term) | IncomingInvoice.invoice_number.ilike(term))
    if date_from:
        q = q.filter(IncomingInvoice.invoice_date >= date_from)
    if date_to:
        q = q.filter(IncomingInvoice.invoice_date <= date_to)
    if status_filter:
        q = q.filter(IncomingInvoice.status == status_filter)
    return q.order_by(IncomingInvoice.invoice_date.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=IncomingInvoiceRead, status_code=status.HTTP_201_CREATED)
def create_incoming_invoice(
    payload: IncomingInvoiceCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> IncomingInvoice:
    """Neue Eingangsrechnung anlegen."""
    inv = IncomingInvoice(
        supplier_name=payload.supplier_name,
        invoice_number=payload.invoice_number,
        invoice_date=payload.invoice_date,
        due_date=payload.due_date,
        net_amount=payload.net_amount,
        vat_amount=payload.vat_amount,
        gross_amount=payload.gross_amount,
        vat_rate=payload.vat_rate,
        status="pending",
        category=payload.category,
        notes=payload.notes,
        is_credit_note=payload.is_credit_note,
        created_by=current_user.id,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    log_audit(
        db,
        user_id=current_user.id,
        entity_type="incoming_invoice",
        entity_id=inv.id,
        action="create",
        new_values={"supplier": inv.supplier_name, "invoice_number": inv.invoice_number},
    )
    db.commit()
    return inv


@router.post("/import-einvoice", response_model=IncomingInvoiceRead, status_code=status.HTTP_201_CREATED)
async def import_einvoice(
    file: Annotated[UploadFile, File(...)],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> IncomingInvoice:
    """E-Rechnung (ZUGFeRD-PDF oder XRechnung-XML) importieren und als Eingangsrechnung speichern.
    Das Original wird unverändert archiviert und per SHA-256 gesichert (GoBD)."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Datei ist leer")
    if len(content) > _MAX_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Datei zu groß (max. 20 MB)")

    try:
        data = parse_einvoice(content)
    except EInvoiceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Die E-Rechnung konnte nicht gelesen werden. Bitte Datei prüfen.",
        ) from exc

    if data["currency"] != "EUR":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Nur Rechnungen in EUR werden unterstützt (Datei: {data['currency']})",
        )

    sha256 = hashlib.sha256(content).hexdigest()
    duplicate = (
        db.query(IncomingInvoice)
        .filter(
            (IncomingInvoice.original_sha256 == sha256)
            | (
                (IncomingInvoice.supplier_name == data["supplier_name"])
                & (IncomingInvoice.invoice_number == data["invoice_number"])
            )
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Diese Rechnung ({data['invoice_number']} von {data['supplier_name']}) wurde bereits erfasst.",
        )

    hints = []
    if data["is_credit_note"]:
        hints.append("Gutschrift / Rechnungskorrektur")
    if data["mixed_vat_rates"]:
        hints.append("Mehrere MwSt-Sätze – Beträge laut Original")
    notes = "Importierte E-Rechnung" + (f" ({'; '.join(hints)})" if hints else "")

    inv_id = uuid.uuid4()
    ext = ".pdf" if data["format"] == FORMAT_ZUGFERD else ".xml"
    original_path = _einvoice_dir() / f"{inv_id}{ext}"
    original_path.write_bytes(content)

    inv = IncomingInvoice(
        id=inv_id,
        supplier_name=data["supplier_name"][:255],
        invoice_number=data["invoice_number"][:100],
        invoice_date=date.fromisoformat(data["invoice_date"]),
        due_date=date.fromisoformat(data["due_date"]) if data["due_date"] else None,
        service_date=date.fromisoformat(data["service_date"]) if data["service_date"] else None,
        net_amount=data["net_amount"],
        vat_amount=data["vat_amount"],
        gross_amount=data["gross_amount"],
        vat_rate=data["vat_rate"],
        status="pending",
        notes=notes,
        is_credit_note=bool(data["is_credit_note"]),
        pdf_path=str(original_path) if data["format"] == FORMAT_ZUGFERD else None,
        einvoice_format=data["format"],
        original_path=str(original_path),
        original_filename=(file.filename or f"e-rechnung{ext}")[:255],
        original_sha256=sha256,
        supplier_vat_id=(data["supplier_vat_id"] or "")[:50] or None,
        created_by=current_user.id,
    )
    db.add(inv)
    try:
        db.flush()
        log_audit(
            db,
            user_id=current_user.id,
            entity_type="incoming_invoice",
            entity_id=inv.id,
            action="import_einvoice",
            new_values={
                "format": data["format"],
                "supplier": inv.supplier_name,
                "invoice_number": inv.invoice_number,
                "sha256": sha256,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        original_path.unlink(missing_ok=True)
        raise
    db.refresh(inv)
    return inv


@router.get("/{invoice_id}", response_model=IncomingInvoiceRead)
def get_incoming_invoice(
    invoice_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> IncomingInvoice:
    """Einzelne Eingangsrechnung abrufen."""
    inv = db.query(IncomingInvoice).filter(IncomingInvoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Eingangsrechnung nicht gefunden")
    return inv


@router.patch("/{invoice_id}", response_model=IncomingInvoiceRead)
def update_incoming_invoice(
    invoice_id: UUID,
    payload: IncomingInvoiceUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> IncomingInvoice:
    """Eingangsrechnung aktualisieren."""
    inv = db.query(IncomingInvoice).filter(IncomingInvoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Eingangsrechnung nicht gefunden")

    changes = payload.model_dump(exclude_unset=True)
    if inv.original_path:
        blocked = set(changes) - _EINVOICE_EDITABLE_FIELDS
        if blocked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Importierte E-Rechnung: Nur Status, Kategorie und Notizen sind änderbar (GoBD).",
            )

    for field, value in changes.items():
        setattr(inv, field, value)

    # Beträge neu berechnen wenn Netto oder MwSt geändert
    if payload.net_amount is not None or payload.vat_rate is not None:
        from decimal import Decimal as D
        net = inv.net_amount
        rate = inv.vat_rate
        inv.vat_amount = (net * rate / 100).quantize(D("0.01"))
        inv.gross_amount = net + inv.vat_amount

    db.commit()
    db.refresh(inv)
    return inv


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_incoming_invoice(
    invoice_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> None:
    """Eingangsrechnung löschen (inkl. PDF-Datei)."""
    inv = db.query(IncomingInvoice).filter(IncomingInvoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Eingangsrechnung nicht gefunden")
    if inv.original_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Importierte E-Rechnungen dürfen nicht gelöscht werden (GoBD-Aufbewahrungspflicht).",
        )
    if inv.pdf_path and os.path.exists(inv.pdf_path):
        os.remove(inv.pdf_path)
    db.delete(inv)
    db.commit()


@router.post("/{invoice_id}/upload-pdf", response_model=IncomingInvoiceRead)
async def upload_pdf(
    invoice_id: UUID,
    file: Annotated[UploadFile, File(...)],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> IncomingInvoice:
    """PDF zur Eingangsrechnung hochladen."""
    inv = db.query(IncomingInvoice).filter(IncomingInvoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Eingangsrechnung nicht gefunden")
    if inv.einvoice_format == FORMAT_ZUGFERD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Diese E-Rechnung hat bereits ein PDF (Original) – Ersetzen nicht erlaubt.",
        )

    if file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Nur PDF, JPEG oder PNG erlaubt")

    content = await file.read()
    if len(content) > _MAX_SIZE:
        raise HTTPException(status_code=400, detail="Datei zu groß (max. 20 MB)")

    # Altes PDF entfernen
    if inv.pdf_path and os.path.exists(inv.pdf_path):
        os.remove(inv.pdf_path)

    upload_dir = _upload_dir()
    ext = Path(file.filename or "doc.pdf").suffix or ".pdf"
    filename = f"{invoice_id}{ext}"
    file_path = upload_dir / filename
    file_path.write_bytes(content)

    inv.pdf_path = str(file_path)
    db.commit()
    db.refresh(inv)
    return inv


@router.get("/{invoice_id}/pdf")
def download_pdf(
    invoice_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FileResponse:
    """PDF der Eingangsrechnung herunterladen."""
    inv = db.query(IncomingInvoice).filter(IncomingInvoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Eingangsrechnung nicht gefunden")
    if not inv.pdf_path or not os.path.exists(inv.pdf_path):
        raise HTTPException(status_code=404, detail="Kein PDF vorhanden")
    ext = Path(inv.pdf_path).suffix
    filename = f"Eingangsrechnung_{inv.invoice_number.replace('/', '-')}{ext}"
    return FileResponse(inv.pdf_path, media_type="application/pdf", filename=filename)


@router.get("/{invoice_id}/original")
def download_original(
    invoice_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FileResponse:
    """Unverändertes Original der importierten E-Rechnung herunterladen."""
    inv = db.query(IncomingInvoice).filter(IncomingInvoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Eingangsrechnung nicht gefunden")
    if not inv.original_path or not os.path.exists(inv.original_path):
        raise HTTPException(status_code=404, detail="Kein E-Rechnungs-Original vorhanden")
    media_type = "application/pdf" if inv.original_path.endswith(".pdf") else "application/xml"
    return FileResponse(inv.original_path, media_type=media_type, filename=inv.original_filename or Path(inv.original_path).name)
