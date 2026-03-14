"""OCR service for document text extraction."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_text_from_file(file_path: str, content_type: str) -> str | None:
    """
    Extract text from document using OCR.
    Supports PDF and images (JPEG, PNG, GIF, WebP).
    Returns None if OCR fails or is not applicable.
    """
    path = Path(file_path)
    if not path.exists():
        return None

    try:
        if content_type == "application/pdf":
            return _ocr_pdf(str(path))
        if content_type in ("image/jpeg", "image/png", "image/gif", "image/webp"):
            return _ocr_image(str(path))
    except Exception as e:
        logger.warning("OCR failed for %s: %s", file_path, e)
        return None
    return None


def _ocr_image(image_path: str) -> str:
    """Extract text from image using Tesseract."""
    import pytesseract
    from PIL import Image

    img = Image.open(image_path)
    text = pytesseract.image_to_string(img, lang="deu+eng")
    return text.strip() if text else ""


def _ocr_pdf(pdf_path: str) -> str:
    """Extract text from PDF. Tries pdfplumber first (embedded text), then OCR for scanned PDFs."""
    try:
        import pdfplumber

        with pdfplumber.open(pdf_path) as pdf:
            parts = []
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    parts.append(t)
            if parts:
                return "\n\n".join(parts).strip()
    except Exception:
        pass

    try:
        from pdf2image import convert_from_path
        import pytesseract

        pages = convert_from_path(pdf_path, dpi=200)
        parts = []
        for page in pages:
            text = pytesseract.image_to_string(page, lang="deu+eng")
            if text.strip():
                parts.append(text.strip())
        return "\n\n".join(parts) if parts else ""
    except Exception as e:
        logger.warning("PDF OCR failed: %s", e)
        return ""
