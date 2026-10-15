"""Buchhaltungs-Export: GoBD-konformes Exportpaket für den Steuerberater."""

import csv
import io
import os
import zipfile
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import require_right
from app.core.database import get_db
from app.models.customer import Customer
from app.models.incoming_invoice import IncomingInvoice
from app.models.invoice import Invoice, InvoiceItem

router = APIRouter(prefix="/accounting", tags=["accounting"])

_STATUS_DE = {
    "issued": "Ausgestellt",
    "partially_paid": "Teilweise bezahlt",
    "paid": "Bezahlt",
    "cancelled": "Storniert",
    "pending": "Offen",
}

_EXPORT_STATUSES = ("issued", "partially_paid", "paid", "cancelled")


def _kunde_name(c: Customer) -> str:
    return c.company_name or f"{c.first_name or ''} {c.last_name or ''}".strip() or str(c.id)


def _format_decimal(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"))).replace(".", ",")


def _write_outgoing_csv(
    invoices: list[Invoice],
    customer_map: dict,
) -> bytes:
    """CSV für Ausgangsrechnungen (B2C oder B2B)."""
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow([
        "Rechnungsnummer", "Typ", "Datum", "Fällig am",
        "Kundenname", "Netto (EUR)", "MwSt (EUR)", "Brutto (EUR)", "Status",
    ])
    for inv in invoices:
        typ = {"cancellation": "Stornorechnung", "correction": "Rechnungskorrektur"}.get(
            getattr(inv, "document_type", "invoice"),
            "Stornorechnung" if inv.invoice_number.startswith("STO-") else "Rechnung",
        )
        writer.writerow([
            inv.invoice_number,
            typ,
            inv.invoice_date.strftime("%d.%m.%Y"),
            inv.due_date.strftime("%d.%m.%Y") if inv.due_date else "",
            customer_map.get(inv.customer_id, ""),
            _format_decimal(inv.net_amount),
            _format_decimal(inv.vat_amount),
            _format_decimal(inv.gross_amount),
            _STATUS_DE.get(inv.status, inv.status),
        ])
    return buf.getvalue().encode("utf-8-sig")


def _write_incoming_csv(invoices: list[IncomingInvoice]) -> bytes:
    """CSV für Eingangsrechnungen."""
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow([
        "Rechnungsnummer", "Lieferant", "Kategorie", "Datum", "Fällig am",
        "Netto (EUR)", "MwSt (EUR)", "Brutto (EUR)", "Status", "Notizen",
    ])
    for inv in invoices:
        writer.writerow([
            inv.invoice_number,
            inv.supplier_name,
            inv.category or "",
            inv.invoice_date.strftime("%d.%m.%Y"),
            inv.due_date.strftime("%d.%m.%Y") if inv.due_date else "",
            _format_decimal(inv.net_amount),
            _format_decimal(inv.vat_amount),
            _format_decimal(inv.gross_amount),
            _STATUS_DE.get(inv.status, inv.status),
            inv.notes or "",
        ])
    return buf.getvalue().encode("utf-8-sig")


@router.get("/export")
def export_accounting(
    date_from: date = Query(..., description="Startdatum (YYYY-MM-DD)"),
    date_to: date = Query(..., description="Enddatum (YYYY-MM-DD)"),
    db: Annotated[Session, Depends(get_db)] = None,
    _=Depends(require_right("accounting")),
) -> Response:
    """GoBD-konformes ZIP-Exportpaket, nach Konten getrennt:
    - ausgangsrechnungen_privat/  (B2C-Kunden)
    - ausgangsrechnungen_haendler/ (B2B-Händler)
    - eingangsrechnungen/         (Kreditorenrechnungen)
    """
    if date_from > date_to:
        raise HTTPException(status_code=400, detail="Startdatum muss vor dem Enddatum liegen")

    # Ausgangsrechnungen laden
    all_invoices = (
        db.query(Invoice)
        .filter(
            Invoice.invoice_date >= date_from,
            Invoice.invoice_date <= date_to,
            Invoice.status.in_(_EXPORT_STATUSES),
        )
        .order_by(Invoice.invoice_date, Invoice.invoice_number)
        .all()
    )

    # Kundennamen + Typen cachen
    customer_ids = {inv.customer_id for inv in all_invoices}
    customers = db.query(Customer).filter(Customer.id.in_(customer_ids)).all()
    customer_map = {c.id: _kunde_name(c) for c in customers}
    customer_type_map = {c.id: c.customer_type for c in customers}

    b2c_invoices = [i for i in all_invoices if customer_type_map.get(i.customer_id) == "B2C"]
    b2b_invoices = [i for i in all_invoices if customer_type_map.get(i.customer_id) == "B2B"]

    # Eingangsrechnungen laden
    incoming = (
        db.query(IncomingInvoice)
        .filter(
            IncomingInvoice.invoice_date >= date_from,
            IncomingInvoice.invoice_date <= date_to,
        )
        .order_by(IncomingInvoice.invoice_date, IncomingInvoice.invoice_number)
        .all()
    )

    zip_buffer = io.BytesIO()
    pdf_errors: list[str] = []

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        from app.services import archive  # noqa: PLC0415

        # --- PDFs Ausgangsrechnungen B2C ---
        for inv in b2c_invoices:
            try:
                pdf_bytes = archive.invoice_document(db, inv, "zugferd", None)
            except Exception as exc:  # noqa: BLE001
                try:
                    pdf_bytes = archive.invoice_document(db, inv, "pdf", None)
                    pdf_errors.append(f"{inv.invoice_number}: ZUGFeRD fehlgeschlagen, normales PDF verwendet ({exc})")
                except Exception as exc2:  # noqa: BLE001
                    pdf_errors.append(f"{inv.invoice_number}: {exc2}")
                    continue
            zf.writestr(f"ausgangsrechnungen_privat/{inv.invoice_number}.pdf", pdf_bytes)

        # --- PDFs Ausgangsrechnungen B2B ---
        for inv in b2b_invoices:
            try:
                pdf_bytes = archive.invoice_document(db, inv, "zugferd", None)
            except Exception as exc:  # noqa: BLE001
                try:
                    pdf_bytes = archive.invoice_document(db, inv, "pdf", None)
                    pdf_errors.append(f"{inv.invoice_number}: ZUGFeRD fehlgeschlagen, normales PDF verwendet ({exc})")
                except Exception as exc2:  # noqa: BLE001
                    pdf_errors.append(f"{inv.invoice_number}: {exc2}")
                    continue
            zf.writestr(f"ausgangsrechnungen_haendler/{inv.invoice_number}.pdf", pdf_bytes)

        # --- PDFs Eingangsrechnungen ---
        for inc in incoming:
            if inc.pdf_path and os.path.exists(inc.pdf_path):
                with open(inc.pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                safe_num = inc.invoice_number.replace("/", "-").replace("\\", "-")
                zf.writestr(f"eingangsrechnungen/{safe_num}_{inc.supplier_name[:30]}.pdf", pdf_bytes)

        # --- CSVs je Konto ---
        zf.writestr("ausgangsrechnungen_privat.csv", _write_outgoing_csv(b2c_invoices, customer_map))
        zf.writestr("ausgangsrechnungen_haendler.csv", _write_outgoing_csv(b2b_invoices, customer_map))
        zf.writestr("eingangsrechnungen.csv", _write_incoming_csv(incoming))

        # --- USt-Zusammenfassung (alle Ausgangsrechnungen) ---
        ust_rows = (
            db.query(
                func.date_trunc("month", Invoice.invoice_date).label("monat"),
                Customer.customer_type.label("typ"),
                InvoiceItem.vat_rate,
                func.sum(InvoiceItem.line_total_net).label("netto"),
            )
            .join(Invoice, InvoiceItem.invoice_id == Invoice.id)
            .join(Customer, Invoice.customer_id == Customer.id)
            .filter(
                Invoice.invoice_date >= date_from,
                Invoice.invoice_date <= date_to,
                Invoice.status.in_(_EXPORT_STATUSES),
            )
            .group_by(
                func.date_trunc("month", Invoice.invoice_date),
                Customer.customer_type,
                InvoiceItem.vat_rate,
            )
            .order_by(
                func.date_trunc("month", Invoice.invoice_date),
                Customer.customer_type,
                InvoiceItem.vat_rate,
            )
            .all()
        )

        ust_buf = io.StringIO()
        ust_writer = csv.writer(ust_buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        ust_writer.writerow([
            "Monat", "Kundentyp", "MwSt-Satz (%)",
            "Netto (EUR)", "MwSt (EUR)", "Brutto (EUR)",
        ])
        for row in ust_rows:
            monat_str = row.monat.strftime("%Y-%m") if row.monat else ""
            netto = Decimal(str(row.netto or 0)).quantize(Decimal("0.01"))
            mwst_satz = Decimal(str(row.vat_rate or 0))
            mwst = (netto * mwst_satz / 100).quantize(Decimal("0.01"))
            brutto = netto + mwst
            ust_writer.writerow([
                monat_str,
                "Privat (B2C)" if row.typ == "B2C" else "Händler (B2B)",
                _format_decimal(mwst_satz),
                _format_decimal(netto),
                _format_decimal(mwst),
                _format_decimal(brutto),
            ])
        zf.writestr("ust_zusammenfassung.csv", ust_buf.getvalue().encode("utf-8-sig"))

        # --- Begleitdokument ---
        hinweise = ""
        if pdf_errors:
            hinweise = f"\nHINWEIS: Bei {len(pdf_errors)} Rechnung(en) konnte kein PDF erzeugt werden:\n"
            hinweise += "\n".join(f"  - {e}" for e in pdf_errors)

        inc_ohne_pdf = [i for i in incoming if not i.pdf_path or not os.path.exists(i.pdf_path)]
        if inc_ohne_pdf:
            hinweise += f"\n\nEINGANGSRECHNUNGEN OHNE PDF: {len(inc_ohne_pdf)} Eingangsrechnung(en) haben kein hochgeladenes PDF:\n"
            hinweise += "\n".join(f"  - {i.invoice_number} ({i.supplier_name})" for i in inc_ohne_pdf)

        readme = (
            f"GoBD-Exportpaket WareVision – Kontengetrennter Export\n"
            f"=====================================================\n"
            f"Exportiert am: {date.today().strftime('%d.%m.%Y')}\n"
            f"Zeitraum: {date_from.strftime('%d.%m.%Y')} bis {date_to.strftime('%d.%m.%Y')}\n"
            f"\n"
            f"Konten im Export\n"
            f"----------------\n"
            f"Ausgangsrechnungen Privat (B2C):   {len(b2c_invoices)} Rechnung(en)\n"
            f"Ausgangsrechnungen Händler (B2B):  {len(b2b_invoices)} Rechnung(en)\n"
            f"Eingangsrechnungen (Kreditoren):   {len(incoming)} Rechnung(en)\n"
            f"\n"
            f"Enthaltene Dateien\n"
            f"------------------\n"
            f"ausgangsrechnungen_privat/       PDFs B2C-Kundenrechnungen (ZUGFeRD 2.1)\n"
            f"ausgangsrechnungen_haendler/     PDFs B2B-Händlerrechnungen (ZUGFeRD 2.1)\n"
            f"eingangsrechnungen/              Hochgeladene Eingangsrechnungs-PDFs\n"
            f"ausgangsrechnungen_privat.csv    CSV Privatkunden (Semikolon, UTF-8 BOM)\n"
            f"ausgangsrechnungen_haendler.csv  CSV Händler (Semikolon, UTF-8 BOM)\n"
            f"eingangsrechnungen.csv           CSV Eingangsrechnungen (Semikolon, UTF-8 BOM)\n"
            f"ust_zusammenfassung.csv          USt nach Monat, Kundentyp und Steuersatz\n"
            f"{hinweise}\n"
        )
        zf.writestr("LIESMICH.txt", readme.encode("utf-8"))

    db.commit()  # nachträglich archivierte Originale speichern
    zip_buffer.seek(0)
    filename = f"Buchhaltung_{date_from.strftime('%Y%m%d')}_{date_to.strftime('%Y%m%d')}.zip"
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# DATEV-Export (Buchungsstapel im DATEV-Format)
# ---------------------------------------------------------------------------

from typing import Literal  # noqa: E402

from pydantic import BaseModel, Field  # noqa: E402

from app.models.user import User  # noqa: E402
from app.services import datev as datev_service  # noqa: E402
from app.services.audit import log_audit  # noqa: E402


class DatevSettingsIn(BaseModel):
    """DATEV-Einstellungen (vom Steuerberater erfragen)."""

    consultant_number: int | None = Field(default=None, ge=1001, le=9999999)
    client_number: int | None = Field(default=None, ge=1, le=99999)
    chart: Literal["SKR03", "SKR04"] = "SKR03"
    account_length: int = Field(default=4, ge=4, le=8)
    fiscal_year_start_month: int = Field(default=1, ge=1, le=12)
    debtor_start: int | None = None
    creditor_start: int | None = None
    lock_bookings: bool = False
    revenue_19: str = ""
    revenue_7: str = ""
    revenue_0: str = ""
    expense_19: str = ""
    expense_7: str = ""
    expense_0: str = ""


def _settings_out(db: Session) -> dict:
    s = datev_service.load_settings(db)
    return {
        "consultant_number": s.consultant_number,
        "client_number": s.client_number,
        "chart": s.chart,
        "account_length": s.account_length,
        "fiscal_year_start_month": s.fiscal_year_start_month,
        "debtor_start": s.debtor_start,
        "creditor_start": s.creditor_start,
        "lock_bookings": s.lock_bookings,
        **s.accounts,
        "account_labels": datev_service.ACCOUNT_LABELS,
        "default_accounts": datev_service.DEFAULT_ACCOUNTS,
        "problems": datev_service.settings_problems(s),
    }


@router.get("/datev/settings")
def get_datev_settings(db: Annotated[Session, Depends(get_db)], _=Depends(require_right("accounting"))) -> dict:
    """DATEV-Einstellungen inkl. Kontenvorschlägen und offenen Punkten."""
    return _settings_out(db)


@router.put("/datev/settings")
def update_datev_settings(
    payload: DatevSettingsIn,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_right("accounting"))],
) -> dict:
    """DATEV-Einstellungen speichern. Leere Konten = Vorschlag des Kontenrahmens."""
    values = payload.model_dump()
    for key in datev_service.ACCOUNT_KEYS:
        values[key] = (values[key] or "").strip()
        if values[key] and not values[key].isdigit():
            raise HTTPException(status_code=400, detail=f"Konto „{datev_service.ACCOUNT_LABELS[key]}“: nur Ziffern erlaubt")
    datev_service.save_settings(db, values)
    log_audit(db, user_id=current_user.id, entity_type="settings", action="datev_settings",
              new_values={k: v for k, v in values.items() if k in ("chart", "account_length", "consultant_number", "client_number")})
    db.commit()
    return _settings_out(db)


def _datev_run(db: Session, date_from: date, date_to: date, include_incoming: bool, persist: bool):
    s = datev_service.load_settings(db)
    problems = datev_service.settings_problems(s)
    if problems:
        raise HTTPException(status_code=400, detail="DATEV-Einstellungen unvollständig: " + " ".join(problems))
    try:
        res = datev_service.collect(db, s, date_from, date_to, persist=persist, include_incoming=include_incoming)
    except datev_service.DatevError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return s, res


@router.get("/datev/preview")
def datev_preview(
    date_from: date = Query(...),
    date_to: date = Query(...),
    include_incoming: bool = True,
    db: Annotated[Session, Depends(get_db)] = None,
    _=Depends(require_right("accounting")),
) -> dict:
    """Vorschau: Anzahl Belege/Buchungen, Summen und Hinweise – ohne etwas zu speichern."""
    s, res = _datev_run(db, date_from, date_to, include_incoming, persist=False)  # speichert nichts

    def total(bookings, dc):
        return str(sum((b.amount for b in bookings if b.debit_credit == dc), Decimal("0")))

    return {
        "fiscal_year_start": datev_service.fiscal_year_start(s, date_from).isoformat(),
        "outgoing_documents": res.outgoing_docs,
        "outgoing_bookings": len(res.outgoing),
        "outgoing_debit": total(res.outgoing, "S"),
        "outgoing_credit": total(res.outgoing, "H"),
        "incoming_documents": res.incoming_docs,
        "incoming_bookings": len(res.incoming),
        "incoming_credit": total(res.incoming, "H"),
        "incoming_debit": total(res.incoming, "S"),
        "new_accounts": res.new_accounts,
        "hints": res.hints,
    }


@router.get("/datev/export")
def datev_export(
    date_from: date = Query(...),
    date_to: date = Query(...),
    include_incoming: bool = True,
    db: Annotated[Session, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(require_right("accounting"))] = None,
) -> Response:
    """DATEV-Export als ZIP (Buchungsstapel Ausgang/Eingang, Personenkonten, LIESMICH)."""
    s, res = _datev_run(db, date_from, date_to, include_incoming, persist=True)
    user = f"{current_user.first_name} {current_user.last_name}".strip() or current_user.email
    content = datev_service.build_export_zip(s, res, date_from, date_to, user)
    log_audit(
        db, user_id=current_user.id, entity_type="accounting", action="datev_export",
        new_values={
            "date_from": date_from.isoformat(), "date_to": date_to.isoformat(),
            "outgoing_bookings": len(res.outgoing), "incoming_bookings": len(res.incoming),
            "new_accounts": res.new_accounts, "hints": len(res.hints),
        },
    )
    db.commit()  # neu vergebene Debitoren-/Kreditorennummern dauerhaft speichern
    filename = f"DATEV_{date_from.strftime('%Y%m%d')}_{date_to.strftime('%Y%m%d')}.zip"
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/datev/accounts")
def datev_accounts(db: Annotated[Session, Depends(get_db)], _=Depends(require_right("accounting"))) -> list[dict]:
    """Bereits vergebene Debitoren- und Kreditorennummern."""
    from app.models.datev import DatevAccount

    rows = db.query(DatevAccount).order_by(DatevAccount.account_number).all()
    return [{"account_number": r.account_number, "kind": r.kind, "name": r.name} for r in rows]
