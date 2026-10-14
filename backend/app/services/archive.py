"""Belegarchiv (GoBD): ausgegebene Dokumente werden einmalig als Original gespeichert.

- Rechnungen, Stornorechnungen und Rechnungskorrekturen beim Ausstellen (PDF und ZUGFeRD),
  Mahnungen beim Setzen der Mahnstufe, Angebote und Bestellungen beim Versenden.
- Danach wird immer das gespeicherte Original ausgeliefert – spätere Änderungen an Firmen- oder
  Kundendaten (z. B. neue Adresse, DSGVO-Anonymisierung) ändern ausgegebene Belege nicht mehr.
- Dateien werden nie überschrieben oder gelöscht; die SHA-256-Prüfsumme wird bei jedem Abruf geprüft.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from collections.abc import Callable
from datetime import date
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.archived_document import ArchivedDocument
from app.services.audit import log_audit

logger = logging.getLogger(__name__)


class ArchiveIntegrityError(Exception):
    """Archivdatei fehlt oder wurde verändert (Prüfsumme stimmt nicht)."""


def archive_root() -> Path:
    """Wurzelverzeichnis des Belegarchivs (im Upload-Volume, damit es gesichert wird)."""
    return Path(get_settings().UPLOAD_DIR) / "belegarchiv"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_once(folder: Path, base: str, data: bytes) -> Path:
    """Datei exklusiv anlegen – vorhandene Dateien werden nie überschrieben.

    Liegt (z. B. nach einem abgebrochenen Vorgang) schon eine Datei mit gleichem Inhalt dort, wird sie
    wiederverwendet; bei anderem Inhalt wird ein neuer Dateiname mit Zähler gewählt.
    """
    for n in range(1, 1000):
        path = folder / (f"{base}.pdf" if n == 1 else f"{base}_{n}.pdf")
        try:
            with open(path, "xb") as fh:
                fh.write(data)
        except FileExistsError:
            if path.read_bytes() == data:
                return path
            continue
        try:
            os.chmod(path, 0o444)  # schreibgeschützt
        except OSError:
            pass
        return path
    raise RuntimeError("Archivdatei konnte nicht angelegt werden")


def find(db: Session, entity_type: str, entity_id: UUID, kind: str) -> ArchivedDocument | None:
    return (
        db.query(ArchivedDocument)
        .filter(ArchivedDocument.entity_type == entity_type, ArchivedDocument.entity_id == entity_id,
                ArchivedDocument.kind == kind)
        .first()
    )


def read(doc: ArchivedDocument) -> bytes:
    """Original lesen und Prüfsumme kontrollieren."""
    path = Path(doc.file_path)
    if not path.is_file():
        raise ArchiveIntegrityError(f"Archivdatei für {doc.document_number} ({doc.kind}) fehlt: {path.name}")
    data = path.read_bytes()
    if _sha256(data) != doc.sha256:
        raise ArchiveIntegrityError(f"Archivdatei für {doc.document_number} ({doc.kind}) wurde verändert (Prüfsumme falsch)")
    return data


def store(db: Session, *, entity_type: str, entity_id: UUID, kind: str, document_number: str, data: bytes,
          user_id: UUID | None, backfilled: bool = False) -> ArchivedDocument:
    """Original einmalig speichern. Existiert es schon, bleibt das vorhandene unverändert."""
    existing = find(db, entity_type, entity_id, kind)
    if existing is not None:
        return existing
    safe_no = re.sub(r"[^A-Za-z0-9._-]", "_", document_number)[:80]
    folder = archive_root() / entity_type / str(date.today().year)
    folder.mkdir(parents=True, exist_ok=True)
    base = f"{safe_no}_{kind}_{str(entity_id)[:8]}"
    path = _write_once(folder, base, data)
    doc = ArchivedDocument(
        entity_type=entity_type, entity_id=entity_id, kind=kind, document_number=document_number,
        file_path=str(path), sha256=_sha256(data), size_bytes=len(data), backfilled=backfilled, created_by=user_id,
    )
    db.add(doc)
    db.flush()
    log_audit(
        db, user_id=user_id, entity_type=entity_type, entity_id=entity_id,
        action="archive_backfill" if backfilled else "archive",
        new_values={"kind": kind, "document_number": document_number, "sha256": doc.sha256},
    )
    return doc


def ensure(db: Session, *, entity_type: str, entity_id: UUID, kind: str, document_number: str,
           generate: Callable[[], bytes], user_id: UUID | None, backfilled: bool = False) -> bytes:
    """Original liefern; fehlt es, wird es jetzt erzeugt und archiviert (backfilled = nachträglich)."""
    doc = find(db, entity_type, entity_id, kind)
    if doc is not None:
        return read(doc)
    data = generate()
    store(db, entity_type=entity_type, entity_id=entity_id, kind=kind, document_number=document_number,
          data=data, user_id=user_id, backfilled=backfilled)
    return data


# ---------------------------------------------------------------------------
# Rechnungen
# ---------------------------------------------------------------------------

def archive_invoice(db: Session, inv, user_id: UUID | None, backfilled: bool = False) -> list[str]:
    """Rechnung (bzw. Storno/Korrektur) als PDF und ZUGFeRD archivieren. Gibt Hinweise zurück."""
    from app.services.pdf import generate_invoice_pdf
    from app.services.zugferd import generate_zugferd_pdf

    hints: list[str] = []
    ensure(db, entity_type="invoice", entity_id=inv.id, kind="pdf", document_number=inv.invoice_number,
           generate=lambda: generate_invoice_pdf(db, inv), user_id=user_id, backfilled=backfilled)
    try:
        ensure(db, entity_type="invoice", entity_id=inv.id, kind="zugferd", document_number=inv.invoice_number,
               generate=lambda: generate_zugferd_pdf(db, inv), user_id=user_id, backfilled=backfilled)
    except ArchiveIntegrityError:
        raise
    except Exception as exc:  # noqa: BLE001 – E-Rechnung darf das Ausstellen nicht blockieren
        logger.warning("ZUGFeRD für %s konnte nicht archiviert werden: %s", inv.invoice_number, exc)
        hints.append(f"{inv.invoice_number}: E-Rechnung (ZUGFeRD) konnte nicht erzeugt werden: {exc}")
        log_audit(db, user_id=user_id, entity_type="invoice", entity_id=inv.id, action="archive_zugferd_failed",
                  new_values={"error": str(exc)[:300]})
    return hints


def invoice_is_final(inv) -> bool:
    """Ausgestellte Belege (nicht Entwürfe) werden aus dem Archiv geliefert."""
    return inv.status != "draft"


def invoice_document(db: Session, inv, kind: str, user_id: UUID | None) -> bytes:
    """PDF („pdf“) oder ZUGFeRD („zugferd“) einer Rechnung: Entwurf live, sonst Original aus dem Archiv."""
    from app.services.pdf import generate_invoice_pdf
    from app.services.zugferd import generate_zugferd_pdf

    gen = (lambda: generate_invoice_pdf(db, inv)) if kind == "pdf" else (lambda: generate_zugferd_pdf(db, inv))
    if not invoice_is_final(inv):
        return gen()
    return ensure(db, entity_type="invoice", entity_id=inv.id, kind=kind, document_number=inv.invoice_number,
                  generate=gen, user_id=user_id, backfilled=True)


def reminder_document(db: Session, inv, user_id: UUID | None, backfilled: bool = True) -> bytes:
    """Mahnbrief der aktuellen Mahnstufe (einmalig archiviert)."""
    from app.services.pdf import generate_reminder_pdf

    level = inv.reminder_level or 1
    return ensure(db, entity_type="invoice", entity_id=inv.id, kind=f"reminder_{level}",
                  document_number=inv.invoice_number, generate=lambda: generate_reminder_pdf(db, inv),
                  user_id=user_id, backfilled=backfilled)


# ---------------------------------------------------------------------------
# Angebote und Bestellungen (Handelsbriefe, § 257 HGB)
# ---------------------------------------------------------------------------

def quote_document(db: Session, quote, user_id: UUID | None, backfilled: bool = True) -> bytes:
    from app.services.quote_pdf import generate_quote_pdf

    if quote.status == "draft":
        return generate_quote_pdf(db, quote)
    return ensure(db, entity_type="quote", entity_id=quote.id, kind="pdf", document_number=quote.quote_number,
                  generate=lambda: generate_quote_pdf(db, quote), user_id=user_id, backfilled=backfilled)


def purchase_order_document(db: Session, order, user_id: UUID | None, backfilled: bool = True) -> bytes:
    from app.services.purchase_order_pdf import generate_purchase_order_pdf

    if order.status == "draft":
        return generate_purchase_order_pdf(db, order)
    return ensure(db, entity_type="purchase_order", entity_id=order.id, kind="pdf",
                  document_number=order.order_number, generate=lambda: generate_purchase_order_pdf(db, order),
                  user_id=user_id, backfilled=backfilled)


# ---------------------------------------------------------------------------
# Übersicht, Nachziehen, Prüfung
# ---------------------------------------------------------------------------

def _missing(db: Session) -> dict[str, list]:
    """Ausgegebene Belege, deren Original noch nicht archiviert ist."""
    from app.models.invoice import Invoice
    from app.models.purchase_order import PurchaseOrder
    from app.models.quote import Quote

    have = {(d.entity_type, d.entity_id, d.kind) for d in db.query(
        ArchivedDocument.entity_type, ArchivedDocument.entity_id, ArchivedDocument.kind).all()}
    invoices = db.query(Invoice).filter(Invoice.status != "draft").order_by(Invoice.invoice_number).all()
    missing_invoices = [i for i in invoices if ("invoice", i.id, "pdf") not in have]
    missing_reminders = [i for i in invoices if i.reminder_level and ("invoice", i.id, f"reminder_{i.reminder_level}") not in have]
    quotes = db.query(Quote).filter(Quote.status != "draft").all()
    orders = db.query(PurchaseOrder).filter(PurchaseOrder.status != "draft").all()
    return {
        "invoices": missing_invoices,
        "reminders": missing_reminders,
        "quotes": [q for q in quotes if ("quote", q.id, "pdf") not in have],
        "purchase_orders": [o for o in orders if ("purchase_order", o.id, "pdf") not in have],
    }


def status(db: Session) -> dict:
    missing = _missing(db)
    return {
        "archived_documents": db.query(ArchivedDocument).count(),
        "backfilled_documents": db.query(ArchivedDocument).filter(ArchivedDocument.backfilled.is_(True)).count(),
        "missing": {k: len(v) for k, v in missing.items()},
        "missing_total": sum(len(v) for v in missing.values()),
    }


def backfill(db: Session, user_id: UUID | None) -> dict:
    """Fehlende Originale für bereits ausgegebene Belege jetzt erzeugen (als „nachträglich“ gekennzeichnet)."""
    missing = _missing(db)
    hints: list[str] = []
    for inv in missing["invoices"]:
        hints += archive_invoice(db, inv, user_id, backfilled=True)
    for inv in missing["reminders"]:
        reminder_document(db, inv, user_id, backfilled=True)
    for q in missing["quotes"]:
        quote_document(db, q, user_id, backfilled=True)
    for o in missing["purchase_orders"]:
        purchase_order_document(db, o, user_id, backfilled=True)
    return {"created": {k: len(v) for k, v in missing.items()}, "hints": hints}


def verify_all(db: Session) -> dict:
    """Alle Archivdateien auf Vorhandensein und Prüfsumme kontrollieren."""
    problems = []
    docs = db.query(ArchivedDocument).order_by(ArchivedDocument.created_at).all()
    for d in docs:
        try:
            read(d)
        except ArchiveIntegrityError as exc:
            problems.append(str(exc))
    return {"checked": len(docs), "problems": problems}
