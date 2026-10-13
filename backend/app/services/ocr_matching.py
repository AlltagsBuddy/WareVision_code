"""OCR-Matching: Kennzeichen und Kundennamen aus extrahiertem Text erkennen."""

import re
import logging
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Deutsches Kennzeichen: 1-3 Buchstaben – 1-2 Buchstaben – 1-4 Ziffern (opt. E/H)
_PLATE_RE = re.compile(
    r'\b([A-ZÄÖÜ]{1,3})[^A-Z0-9]{0,2}([A-Z]{1,2})[^A-Z0-9]{0,2}(\d{1,4}[EH]?)\b',
    re.UNICODE | re.IGNORECASE,
)

# VIN: 17 alphanumerische Zeichen (ohne I, O, Q)
_VIN_RE = re.compile(r'\b([A-HJ-NPR-Z0-9]{17})\b')


def _normalize(s: str) -> str:
    return re.sub(r'[\s\-_/]', '', s).upper()


def _find_plates(text: str) -> set[str]:
    """Alle Kennzeichen-ähnlichen Muster aus Text extrahieren."""
    plates = set()
    for m in _PLATE_RE.finditer(text.upper()):
        plates.add(f"{m.group(1)}-{m.group(2)}-{m.group(3)}")
    return plates


def _find_vins(text: str) -> set[str]:
    return {m.group(1).upper() for m in _VIN_RE.finditer(text)}


def match_vehicle(db: Session, text: str):
    """Fahrzeug aus OCR-Text anhand Kennzeichen oder FIN erkennen."""
    from app.models.vehicle import Vehicle

    found_plates = _find_plates(text)
    found_vins = _find_vins(text)

    if not found_plates and not found_vins:
        return None

    vehicles = db.query(Vehicle).all()
    for v in vehicles:
        if v.license_plate and _normalize(v.license_plate) in {_normalize(p) for p in found_plates}:
            return v
        if v.vin and v.vin.upper() in found_vins:
            return v
    return None


def match_customer(db: Session, text: str):
    """Kunden aus OCR-Text anhand Name oder E-Mail erkennen."""
    from app.models.customer import Customer

    text_upper = text.upper()
    text_lower = text.lower()

    customers = db.query(Customer).all()
    # Längste Treffer zuerst prüfen (verhindert Kurzname-Fehlmatch)
    candidates = []
    for c in customers:
        names = []
        if c.company_name and len(c.company_name) >= 4:
            names.append(c.company_name)
        full = f"{c.first_name or ''} {c.last_name or ''}".strip()
        if len(full) >= 5:
            names.append(full)
        if c.email and len(c.email) >= 6:
            names.append(c.email)
        candidates.append((c, names))

    # Längste Namen zuerst testen
    candidates.sort(key=lambda x: max((len(n) for n in x[1]), default=0), reverse=True)

    for c, names in candidates:
        for name in names:
            if name.upper() in text_upper or name.lower() in text_lower:
                return c
    return None


def match_document_entities(db: Session, extracted_text: str) -> tuple:
    """Gibt (Customer | None, Vehicle | None) zurück."""
    try:
        vehicle = match_vehicle(db, extracted_text)
    except Exception as e:
        logger.warning("Fahrzeug-Matching fehlgeschlagen: %s", e)
        vehicle = None
    try:
        customer = match_customer(db, extracted_text)
    except Exception as e:
        logger.warning("Kunden-Matching fehlgeschlagen: %s", e)
        customer = None
    return customer, vehicle
