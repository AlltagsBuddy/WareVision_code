"""PDF/A-3-Unterstützung für Rechnungs-PDFs (ZUGFeRD/Factur-X).

PDF/A verlangt u. a. eingebettete Schriften und ein Farbprofil (OutputIntent).
- Schriften: Liberation Sans ist maßgleich zu Helvetica/Arial. Sie wird unter den
  Helvetica-Namen registriert, damit alle vorhandenen PDF-Layouts unverändert bleiben,
  die Schrift aber in die PDF eingebettet wird.
- Farbprofil: sRGB IEC61966-2.1 (ICC v2, gemeinfrei, Graeme W. Gill / ArgyllCMS).
"""

import logging
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, NameObject, NumberObject, StreamObject, TextStringObject
from reportlab.lib.fonts import addMapping
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

# Suchpfade für Liberation Sans (Debian-Paket fonts-liberation bzw. fonts-liberation2)
_FONT_DIRS = (
    Path("/usr/share/fonts/truetype/liberation"),
    Path("/usr/share/fonts/truetype/liberation2"),
)
_FONT_FILES = {
    "Helvetica": "LiberationSans-Regular.ttf",
    "Helvetica-Bold": "LiberationSans-Bold.ttf",
    "Helvetica-Oblique": "LiberationSans-Italic.ttf",
    "Helvetica-BoldOblique": "LiberationSans-BoldItalic.ttf",
}
_ICC_PATH = Path(__file__).resolve().parent.parent / "assets" / "sRGB.icc"
_OUTPUT_CONDITION = "sRGB IEC61966-2.1"

_fonts_embedded: bool | None = None


def register_embedded_fonts() -> bool:
    """Liberation Sans als einbettbare Schrift unter den Helvetica-Namen registrieren.

    Gibt True zurück, wenn die Schriften eingebettet werden (PDF/A-fähig).
    Fehlen die Schriftdateien (z. B. lokale Windows-Entwicklung), bleibt Helvetica aktiv.
    """
    global _fonts_embedded
    if _fonts_embedded is not None:
        return _fonts_embedded

    for font_dir in _FONT_DIRS:
        paths = {name: font_dir / file for name, file in _FONT_FILES.items()}
        if all(p.is_file() for p in paths.values()):
            for name, path in paths.items():
                pdfmetrics.registerFont(TTFont(name, str(path)))
            # Zuordnung für <b>/<i> in Paragraphen
            addMapping("Helvetica", 0, 0, "Helvetica")
            addMapping("Helvetica", 1, 0, "Helvetica-Bold")
            addMapping("Helvetica", 0, 1, "Helvetica-Oblique")
            addMapping("Helvetica", 1, 1, "Helvetica-BoldOblique")
            _fonts_embedded = True
            return True

    logger.warning("Liberation-Schriften nicht gefunden – PDFs ohne eingebettete Schrift (kein PDF/A).")
    _fonts_embedded = False
    return False


def add_output_intent(pdf_bytes: bytes) -> bytes:
    """sRGB-Farbprofil als PDF/A-OutputIntent ergänzen (falls noch nicht vorhanden)."""
    if not _ICC_PATH.is_file():
        logger.warning("Farbprofil %s fehlt – OutputIntent nicht gesetzt.", _ICC_PATH)
        return pdf_bytes

    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter(clone_from=reader)
    root = writer._root_object
    if NameObject("/OutputIntents") in root:
        return pdf_bytes

    icc = StreamObject()
    icc.set_data(_ICC_PATH.read_bytes())
    icc.update({NameObject("/N"): NumberObject(3)})
    icc_ref = writer._add_object(icc)

    intent = DictionaryObject({
        NameObject("/Type"): NameObject("/OutputIntent"),
        NameObject("/S"): NameObject("/GTS_PDFA1"),
        NameObject("/OutputConditionIdentifier"): TextStringObject(_OUTPUT_CONDITION),
        NameObject("/Info"): TextStringObject(_OUTPUT_CONDITION),
        NameObject("/DestOutputProfile"): icc_ref,
    })
    root[NameObject("/OutputIntents")] = ArrayObject([writer._add_object(intent)])

    out = BytesIO()
    writer.write(out)
    return out.getvalue()
