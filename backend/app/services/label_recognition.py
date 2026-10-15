"""Etikett-Foto mit KI auslesen (Backup, wenn keine Lieferantendaten zum Barcode vorliegen).

Das Foto wird verkleinert und an die Anthropic Messages API geschickt (derselbe API-Key wie die
KI-Hilfe in den Einstellungen). Zurück kommen nur Vorschläge (Bezeichnung, Hersteller, Teilenummer,
Barcode); sie werden im Formular vor dem Speichern geprüft. Das Foto wird nicht gespeichert.
Hinweis an Nutzer: nur das Etikett fotografieren – keine Personen oder Kundendaten.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import re
import urllib.error
import urllib.request

from app.services.barcode import clean_barcode, looks_like_gtin
from app.services.help_assistant import ANTHROPIC_URL, ANTHROPIC_VERSION, DEFAULT_MODEL

logger = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 15 * 1024 * 1024
MAX_SIDE = 1568
TIMEOUT_SECONDS = 45

PROMPT = (
    "Das Foto zeigt das Etikett oder die Verpackung eines Ersatzteils bzw. Zubehörs für Quads oder "
    "Motorräder. Lies nur ab, was auf dem Etikett steht – nichts erfinden oder raten.\n"
    "Antworte ausschließlich mit einem JSON-Objekt mit diesen Schlüsseln (fehlende Angaben = null):\n"
    '{"name": "kurze deutsche Artikelbezeichnung", "manufacturer": "Hersteller/Marke", '
    '"manufacturer_part_number": "Teilenummer des Herstellers", "barcode": "EAN/GTIN nur Ziffern", '
    '"description": "weitere Angaben vom Etikett, z. B. Größe, Menge, Spezifikation"}'
)


class LabelError(Exception):
    """Fehler bei der Erkennung (Meldung ist für den Nutzer gedacht)."""


def _prepare_image(content: bytes) -> bytes:
    from PIL import Image, ImageOps

    try:
        img = Image.open(io.BytesIO(content))
        img = ImageOps.exif_transpose(img).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise LabelError("Das Bild konnte nicht gelesen werden.") from exc
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=85)
    return out.getvalue()


def _parse_answer(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise LabelError("Auf dem Foto wurde kein lesbares Etikett erkannt.")
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError as exc:
        raise LabelError("Auf dem Foto wurde kein lesbares Etikett erkannt.") from exc
    out = {}
    for key, limit in (("name", 500), ("manufacturer", 150), ("manufacturer_part_number", 100),
                       ("description", 2000)):
        v = data.get(key)
        out[key] = str(v).strip()[:limit] if v not in (None, "", "null") else None
    bc = clean_barcode(str(data.get("barcode") or ""))
    out["barcode"] = bc if looks_like_gtin(bc) else None
    if not any(out.values()):
        raise LabelError("Auf dem Foto wurde kein lesbares Etikett erkannt.")
    return out


def recognize(content: bytes, api_key: str, model: str | None) -> dict:
    """Etikett-Foto auswerten; liefert Vorschläge oder wirft LabelError."""
    if not content:
        raise LabelError("Kein Bild übermittelt.")
    if len(content) > MAX_IMAGE_BYTES:
        raise LabelError("Das Bild ist zu groß (höchstens 15 MB).")
    jpeg = _prepare_image(content)
    payload = json.dumps({
        "model": model or DEFAULT_MODEL,
        "max_tokens": 600,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                             "data": base64.b64encode(jpeg).decode("ascii")}},
                {"type": "text", "text": PROMPT},
            ],
        }],
    }).encode("utf-8")
    req = urllib.request.Request(ANTHROPIC_URL, data=payload, method="POST", headers={
        "x-api-key": api_key, "anthropic-version": ANTHROPIC_VERSION, "content-type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        logger.warning("Etikett-Erkennung: HTTP %s", exc.code)
        if exc.code in (401, 403):
            raise LabelError("Der KI-Zugang (API-Key) ist ungültig. Bitte unter Einstellungen prüfen.") from exc
        if exc.code == 429:
            raise LabelError("Die KI ist gerade ausgelastet. Bitte gleich noch einmal versuchen.") from exc
        raise LabelError(f"Die KI ist momentan nicht erreichbar (Fehler {exc.code}).") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning("Etikett-Erkennung nicht erreichbar: %s", exc)
        raise LabelError("Die KI ist momentan nicht erreichbar.") from exc
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    return _parse_answer(text)
