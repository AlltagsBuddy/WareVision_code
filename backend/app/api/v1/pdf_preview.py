"""PDF-Vorschau als Bilder – für Handys/Tablets, deren Browser PDFs nicht in der Seite anzeigen
(z. B. Chrome auf Android bietet nur den Download an). Das PDF wird nur umgewandelt, nicht gespeichert."""

import base64
import io
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/pdf-preview", tags=["pdf-preview"])

MAX_BYTES = 25 * 1024 * 1024
MAX_PAGES = 20
DPI = 110  # gut lesbar auf dem Handy, kleine Datenmenge


@router.post("")
async def render_pdf_preview(
    file: Annotated[UploadFile, File(...)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """PDF-Seiten als PNG-Bilder (Data-URLs) zurückgeben."""
    from pdf2image import convert_from_bytes, pdfinfo_from_bytes

    content = await file.read()
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Keine PDF-Datei.")
    if len(content) > MAX_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PDF zu groß für die Vorschau.")
    try:
        total = int(pdfinfo_from_bytes(content).get("Pages", 1))
        images = convert_from_bytes(content, dpi=DPI, first_page=1, last_page=min(total, MAX_PAGES), fmt="png")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Vorschau konnte nicht erstellt werden.") from exc
    pages = []
    for img in images:
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        pages.append("data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii"))
    return {"pages": pages, "page_count": total, "truncated": total > MAX_PAGES}
