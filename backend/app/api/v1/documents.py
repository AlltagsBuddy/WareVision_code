"""Documents API."""

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile, status
from typing import Annotated
from uuid import UUID

from fastapi.responses import FileResponse

from app.services.ocr import extract_text_from_file
from app.services.audit import log_audit
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentRead, DocumentAssign

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
}

MAX_SIZE = 10 * 1024 * 1024  # 10 MB


def _ensure_upload_dir() -> Path:
    settings = get_settings()
    path = Path(settings.UPLOAD_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


@router.get("", response_model=list[DocumentRead])
def list_documents(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    customer_id: UUID | None = None,
    vehicle_id: UUID | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[Document]:
    """List documents, optionally filtered by customer or vehicle."""
    query = db.query(Document)
    if customer_id:
        query = query.filter(Document.customer_id == customer_id)
    if vehicle_id:
        query = query.filter(Document.vehicle_id == vehicle_id)
    return query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: Annotated[UploadFile, File()],
    customer_id: Annotated[str | None, Form()] = None,
    vehicle_id: Annotated[str | None, Form()] = None,
    db: Annotated[Session, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
) -> Document:
    """Upload a document."""
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dateiname fehlt")
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dateityp nicht erlaubt. Erlaubt: PDF, JPEG, PNG, GIF, WebP",
        )
    data = await file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Datei zu groß (max. 10 MB)",
        )
    upload_dir = _ensure_upload_dir()
    ext = Path(file.filename).suffix or ".bin"
    safe_name = f"{uuid.uuid4().hex}{ext}"
    file_path = upload_dir / safe_name
    with open(file_path, "wb") as f:
        f.write(data)
    cust_uuid = None
    veh_uuid = None
    if customer_id:
        try:
            cust_uuid = UUID(customer_id)
        except ValueError:
            pass
    if vehicle_id:
        try:
            veh_uuid = UUID(vehicle_id)
        except ValueError:
            pass
    doc = Document(
        customer_id=cust_uuid,
        vehicle_id=veh_uuid,
        filename=file.filename,
        content_type=content_type,
        file_path=str(file_path),
        file_size=len(data),
        created_by=current_user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    try:
        extracted = extract_text_from_file(str(file_path), content_type)
        if extracted:
            doc.extracted_text = extracted[:50000]
            db.commit()
            db.refresh(doc)
    except Exception:
        pass

    return doc


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(
    document_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Document:
    """Get document metadata."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden")
    return doc


@router.get("/{document_id}/download")
def download_document(
    document_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FileResponse:
    """Download document file."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden")
    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Datei nicht gefunden")
    return FileResponse(
        path=doc.file_path,
        filename=doc.filename,
        media_type=doc.content_type,
    )


@router.post("/{document_id}/extract-text", response_model=DocumentRead)
def extract_document_text(
    document_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Document:
    """Trigger OCR/text extraction for document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden")
    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Datei nicht gefunden")
    try:
        extracted = extract_text_from_file(doc.file_path, doc.content_type)
        doc.extracted_text = (extracted[:50000] if extracted else None)
        db.commit()
        db.refresh(doc)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Textextraktion fehlgeschlagen: {str(e)}",
        )
    return doc


@router.patch("/{document_id}", response_model=DocumentRead)
def update_document(
    document_id: UUID,
    payload: DocumentAssign,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Document:
    """Update document assignment (customer, vehicle)."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden")
    if payload.customer_id is not None:
        doc.customer_id = payload.customer_id
    if payload.vehicle_id is not None:
        doc.vehicle_id = payload.vehicle_id
    db.commit()
    db.refresh(doc)
    return doc


@router.post("/{document_id}/send-email")
def send_document_email(
    document_id: UUID,
    payload: dict = Body(default_factory=dict),
    db: Annotated[Session, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Dokument per E-Mail versenden. recipient_email optional (sonst Kunden-E-Mail)."""
    from app.services.email import send_email_with_attachment

    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden")
    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Datei nicht gefunden")

    recipient = (payload or {}).get("recipient_email", "").strip() if payload else ""
    if not recipient and doc.customer_id:
        recipient = (doc.customer.email or "").strip()
    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Keine E-Mail-Adresse. Bitte Empfänger angeben oder Dokument einem Kunden mit E-Mail zuordnen.",
        )

    with open(doc.file_path, "rb") as f:
        file_data = f.read()

    subject = f"Dokument: {doc.filename}"
    body = f"""Sehr geehrte Damen und Herren,

anbei erhalten Sie das angehängte Dokument.

Mit freundlichen Grüßen
"""

    send_email_with_attachment(
        db,
        to_email=recipient,
        subject=subject,
        body=body,
        attachment_filename=doc.filename,
        attachment_data=file_data,
        attachment_content_type=doc.content_type,
    )

    log_audit(
        db,
        user_id=current_user.id,
        entity_type="document",
        entity_id=doc.id,
        action="email_sent",
        new_values={
            "recipient_email": recipient,
            "subject": subject,
            "attachment_filename": doc.filename,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    db.commit()

    return {"message": "Dokument wurde per E-Mail versendet.", "recipient": recipient}


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Delete document and file."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nicht gefunden")
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except OSError:
            pass
    db.delete(doc)
    db.commit()
