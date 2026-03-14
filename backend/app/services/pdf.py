"""PDF generation for invoices."""

from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.invoice import Invoice
from sqlalchemy.orm import Session


def _get_customer_name(inv: Invoice) -> str:
    """Get customer display name."""
    c = inv.customer
    if c.company_name:
        return c.company_name
    parts = [c.first_name or "", c.last_name or ""]
    return " ".join(p).strip() or (c.email or "–")


def generate_invoice_pdf(db: Session, inv: Invoice) -> bytes:
    """Generate invoice PDF, return bytes."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("WareVision – Warenwirtschaft", styles["Title"]))
    story.append(Paragraph("Rechnung", styles["Heading1"]))
    story.append(Spacer(1, 10 * mm))

    story.append(Paragraph(f"<b>Rechnungsnummer:</b> {inv.invoice_number}", styles["Normal"]))
    story.append(Paragraph(f"<b>Datum:</b> {inv.invoice_date.strftime('%d.%m.%Y')}", styles["Normal"]))
    if inv.due_date:
        story.append(Paragraph(f"<b>Fällig:</b> {inv.due_date.strftime('%d.%m.%Y')}", styles["Normal"]))
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph("<b>Rechnungsadresse:</b>", styles["Normal"]))
    story.append(Paragraph(_get_customer_name(inv), styles["Normal"]))
    story.append(Spacer(1, 10 * mm))

    data = [["Pos", "Beschreibung", "Menge", "Einheit", "Einzelpreis", "MwSt %", "Gesamt netto"]]
    for i, item in enumerate(inv.items, 1):
        data.append([
            str(i),
            item.description[:50] + ("…" if len(item.description) > 50 else ""),
            str(item.quantity),
            item.unit or "Stk",
            f"{item.unit_price:.2f} €",
            f"{item.vat_rate:.1f}",
            f"{item.line_total_net:.2f} €",
        ])

    t = Table(data, colWidths=[25 * mm, 60 * mm, 25 * mm, 25 * mm, 35 * mm, 25 * mm, 35 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#334155")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(t)
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph(f"<b>Netto:</b> {inv.net_amount:.2f} €", styles["Normal"]))
    story.append(Paragraph(f"<b>MwSt:</b> {inv.vat_amount:.2f} €", styles["Normal"]))
    story.append(Paragraph(f"<b>Brutto:</b> {inv.gross_amount:.2f} €", styles["Normal"]))
    if inv.notes:
        story.append(Spacer(1, 5 * mm))
        story.append(Paragraph(f"<b>Anmerkungen:</b> {inv.notes}", styles["Normal"]))

    doc.build(story)
    return buffer.getvalue()
