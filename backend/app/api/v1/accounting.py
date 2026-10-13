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

from app.api.deps import require_admin
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
        typ = "Stornorechnung" if inv.invoice_number.startswith("STO-") else "Rechnung"
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
    _=Depends(require_admin),
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
        from app.services.zugferd import generate_zugferd_pdf  # noqa: PLC0415
        from app.services.pdf import generate_invoice_pdf  # noqa: PLC0415

        # --- PDFs Ausgangsrechnungen B2C ---
        for inv in b2c_invoices:
            try:
                pdf_bytes = generate_zugferd_pdf(db, inv)
            except Exception as exc:  # noqa: BLE001
                try:
                    pdf_bytes = generate_invoice_pdf(db, inv)
                    pdf_errors.append(f"{inv.invoice_number}: ZUGFeRD fehlgeschlagen, normales PDF verwendet ({exc})")
                except Exception as exc2:  # noqa: BLE001
                    pdf_errors.append(f"{inv.invoice_number}: {exc2}")
                    continue
            zf.writestr(f"ausgangsrechnungen_privat/{inv.invoice_number}.pdf", pdf_bytes)

        # --- PDFs Ausgangsrechnungen B2B ---
        for inv in b2b_invoices:
            try:
                pdf_bytes = generate_zugferd_pdf(db, inv)
            except Exception as exc:  # noqa: BLE001
                try:
                    pdf_bytes = generate_invoice_pdf(db, inv)
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

    zip_buffer.seek(0)
    filename = f"Buchhaltung_{date_from.strftime('%Y%m%d')}_{date_to.strftime('%Y%m%d')}.zip"
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
