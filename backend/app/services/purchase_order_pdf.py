"""PDF für Bestellungen beim Lieferanten (gleiches Layout wie Rechnung und Angebot)."""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.models.purchase_order import PurchaseOrder
from app.services.pdf import (
    _BORDER,
    _HEADER_BG,
    _ROW_ALT,
    _build_logo_cell,
    _fmt_eur,
    _fmt_rate,
    _get_company_settings,
    _vat_breakdown,
)


def _supplier_address_lines(order: PurchaseOrder) -> list[str]:
    """Anschrift des Lieferanten."""
    s = order.supplier
    if s is None:
        return []
    lines = [s.name]
    if s.contact_person:
        lines.append(f"z. Hd. {s.contact_person}")
    street = " ".join(x for x in (s.street, s.house_number) if x)
    if street:
        lines.append(street)
    city = " ".join(x for x in (s.postal_code, s.city) if x)
    if city:
        lines.append(city)
    if s.country and s.country.strip().lower() not in ("deutschland", "de", "germany"):
        lines.append(s.country)
    return lines


def generate_purchase_order_pdf(db: Session, order: PurchaseOrder) -> bytes:
    """Bestellung als PDF erzeugen und Bytes zurückgeben."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=20 * mm, leftMargin=20 * mm, topMargin=18 * mm, bottomMargin=20 * mm,
        title=f"Bestellung {order.order_number}",
    )
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    small = ParagraphStyle("Small", parent=normal, fontSize=8, leading=11)
    normal_sm = ParagraphStyle("NormalSm", parent=normal, fontSize=9, leading=13)
    cell = ParagraphStyle("Cell", parent=normal, fontSize=9, leading=11)
    cell_grey = ParagraphStyle("CellGrey", parent=cell, fontSize=7.5, leading=9, textColor=colors.HexColor("#555555"))
    th = ParagraphStyle("Th", parent=normal, fontSize=9, textColor=colors.white, fontName="Helvetica-Bold")
    story = []

    s = _get_company_settings(db)
    company_name = s.get("company_name", "").strip() or "WareVision"
    address_lines = [x.strip() for x in s.get("company_address", "").replace("\r\n", "\n").split("\n") if x.strip()]

    # --- Kopf: Firmendaten | Logo ---
    company_lines = [f"<b>{escape(company_name)}</b>"] + [escape(x) for x in address_lines]
    for label, key in (("E-Mail", "company_email"), ("Tel.", "company_phone"), ("Web", "company_website"), ("USt-IdNr.", "company_vat_id")):
        if s.get(key, "").strip():
            company_lines.append(f"{label}: {escape(s[key].strip())}")
    company_para = Paragraph("<br/>".join(company_lines), small)
    logo = _build_logo_cell(s.get("company_logo_path", "").strip(), max_height=22 * mm)
    if logo:
        header = Table([[company_para, logo]], colWidths=[120 * mm, 50 * mm])
        header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (1, 0), (1, 0), "RIGHT")]))
    else:
        header = Table([[company_para]], colWidths=[170 * mm])
        header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story += [header, Spacer(1, 4 * mm), HRFlowable(width="100%", thickness=1.5, color=_HEADER_BG), Spacer(1, 6 * mm)]

    story.append(Paragraph("<b>Bestellung</b>", ParagraphStyle("T", parent=normal, fontSize=18, leading=22, fontName="Helvetica-Bold")))
    story.append(Spacer(1, 6 * mm))

    # --- Meta | Lieferantenadresse ---
    meta = [
        f"<b>Bestell-Nr.:</b> {escape(order.order_number)}",
        f"<b>Datum:</b> {order.order_date.strftime('%d.%m.%Y')}",
    ]
    if order.supplier and order.supplier.customer_number:
        meta.append(f"<b>Unsere Kundennr.:</b> {escape(order.supplier.customer_number)}")
    if order.expected_date:
        meta.append(f"<b>Gewünschter Liefertermin:</b> {order.expected_date.strftime('%d.%m.%Y')}")
    supplier_lines = _supplier_address_lines(order)
    addr = "<b>Lieferant:</b><br/>" + "<br/>".join(escape(x) for x in supplier_lines)
    meta_table = Table([[Paragraph("<br/>".join(meta), normal_sm), Paragraph(addr, normal_sm)]], colWidths=[85 * mm, 85 * mm])
    meta_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story += [meta_table, Spacer(1, 6 * mm)]
    story.append(Paragraph("Wir bestellen zu Ihren bekannten Bedingungen:", normal_sm))
    story.append(Spacer(1, 4 * mm))

    # --- Positionen ---
    data = [[Paragraph(f"<b>{h}</b>", th) for h in ("Pos", "Ihre Art.-Nr.", "Bezeichnung", "Menge", "Einzelpreis", "Gesamt netto")]]
    for it in order.items:
        desc = [Paragraph(escape(it.description), cell)]
        if it.article_number:
            desc.append(Paragraph(f"Unsere Nr.: {escape(it.article_number)}", cell_grey))
        data.append([
            str(it.position),
            Paragraph(escape(it.supplier_article_number or "–"), cell),
            desc,
            f"{it.quantity} {it.unit or 'Stk'}",
            _fmt_eur(it.unit_price),
            _fmt_eur(it.line_total_net),
        ])
    n = len(data)
    t = Table(data, colWidths=[11 * mm, 30 * mm, 59 * mm, 20 * mm, 24 * mm, 26 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ("TOPPADDING", (0, 0), (-1, 0), 6), ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TOPPADDING", (0, 1), (-1, -1), 5), ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _ROW_ALT]),
        ("BOX", (0, 0), (-1, -1), 0.6, _BORDER), ("LINEBELOW", (0, 0), (-1, 0), 0.6, _BORDER),
        ("INNERGRID", (0, 1), (-1, -1), 0.4, _BORDER),
        ("ALIGN", (3, 1), (-1, n), "RIGHT"),
    ]))
    story += [t, Spacer(1, 8 * mm)]

    # --- Summen ---
    breakdown = _vat_breakdown(order.items)
    sums = [["Summe netto:", _fmt_eur(order.net_amount)]]
    for rate, basis, tax in breakdown:
        label = f"zzgl. MwSt {_fmt_rate(rate)}" + (f" auf {_fmt_eur(basis)}" if len(breakdown) > 1 else "")
        sums.append([f"{label}:", _fmt_eur(tax)])
    sums.append(["Gesamt (brutto):", _fmt_eur(order.gross_amount)])
    st = Table(sums, colWidths=[60 * mm, 30 * mm], hAlign="RIGHT")
    st.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9), ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE", (0, -1), (-1, -1), 1.0, colors.black), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(st)

    # --- Hinweise ---
    notes = ["Die Preise sind Netto-Einkaufspreise laut unseren Unterlagen; maßgeblich ist Ihre Auftragsbestätigung."]
    if address_lines:
        notes.append("Lieferadresse: " + ", ".join([company_name] + address_lines))
    notes.append(f"Bitte geben Sie auf Lieferschein und Rechnung unsere Bestell-Nr. {order.order_number} an.")
    if order.notes:
        notes.append(order.notes)
    for note in notes:
        story += [Spacer(1, 3 * mm), Paragraph(escape(note).replace("\n", "<br/>"), normal_sm)]

    doc.build(story)
    return buffer.getvalue()
