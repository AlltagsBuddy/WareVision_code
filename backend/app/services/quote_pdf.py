"""PDF für Angebote und Kostenvoranschläge (gleiches Layout wie die Rechnung)."""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.models.quote import QUOTE_TYPE_ESTIMATE, Quote
from app.services.pdf import (
    _BORDER,
    _DEFAULT_EXEMPTION_NOTE,
    _HEADER_BG,
    _ROW_ALT,
    _build_logo_cell,
    _fmt_eur,
    _fmt_qty,
    _fmt_rate,
    _get_company_settings,
    _get_customer_address_lines,
    _get_customer_name,
    _vat_breakdown,
)

# Hinweis für Kostenvoranschläge (§ 649 BGB: unverbindlicher Kostenanschlag, Anzeigepflicht bei Überschreitung)
ESTIMATE_NOTE = (
    "Dieser Kostenvoranschlag ist unverbindlich; eine Gewähr für seine Richtigkeit wird nicht übernommen. "
    "Zeichnet sich ab, dass die Kosten wesentlich überschritten werden, informieren wir Sie unverzüglich "
    "vor der weiteren Ausführung (§ 649 BGB)."
)


def _vehicle_line(quote: Quote) -> str | None:
    """Fahrzeugbeschreibung für das PDF (Hersteller/Modell/Kennzeichen, soweit vorhanden)."""
    v = quote.vehicle
    if v is None:
        return None
    parts: list[str] = []
    manufacturer = getattr(getattr(v, "manufacturer", None), "name", None)
    model = getattr(getattr(v, "vehicle_model", None), "name", None) or getattr(v, "model_name_free", None)
    for p in (manufacturer, model):
        if p:
            parts.append(str(p))
    if getattr(v, "license_plate", None):
        parts.append(f"Kennzeichen {v.license_plate}")
    if getattr(v, "vin", None):
        parts.append(f"FIN {v.vin}")
    return ", ".join(parts) or None


def generate_quote_pdf(db: Session, quote: Quote) -> bytes:
    """Angebot bzw. Kostenvoranschlag als PDF erzeugen und Bytes zurückgeben."""
    is_estimate = quote.quote_type == QUOTE_TYPE_ESTIMATE
    title = "Kostenvoranschlag" if is_estimate else "Angebot"

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=20 * mm, leftMargin=20 * mm, topMargin=18 * mm, bottomMargin=20 * mm,
        title=f"{title} {quote.quote_number}",
    )
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    small = ParagraphStyle("Small", parent=normal, fontSize=8, leading=11)
    normal_sm = ParagraphStyle("NormalSm", parent=normal, fontSize=9, leading=13)
    cell = ParagraphStyle("Cell", parent=normal, fontSize=9, leading=11)
    th = ParagraphStyle("Th", parent=normal, fontSize=9, textColor=colors.white, fontName="Helvetica-Bold")
    story = []

    s = _get_company_settings(db)
    company_name = s.get("company_name", "").strip() or "WareVision"

    # --- Kopf: Firmendaten | Logo ---
    company_lines = [f"<b>{escape(company_name)}</b>"]
    for line in s.get("company_address", "").replace("\r\n", "\n").split("\n"):
        if line.strip():
            company_lines.append(escape(line.strip()))
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

    story.append(Paragraph(f"<b>{title}</b>", ParagraphStyle("T", parent=normal, fontSize=18, leading=22, fontName="Helvetica-Bold")))
    if quote.subject:
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(escape(quote.subject), ParagraphStyle("Sub", parent=normal, fontSize=11, leading=14)))
    story.append(Spacer(1, 6 * mm))

    # --- Meta | Kundenadresse ---
    meta = [
        f"<b>{title}s-Nr.:</b> {escape(quote.quote_number)}" if not is_estimate else f"<b>Nr.:</b> {escape(quote.quote_number)}",
        f"<b>Datum:</b> {quote.quote_date.strftime('%d.%m.%Y')}",
    ]
    if quote.valid_until:
        meta.append(f"<b>Gültig bis:</b> {quote.valid_until.strftime('%d.%m.%Y')}")
    vehicle = _vehicle_line(quote)
    if vehicle:
        meta.append(f"<b>Fahrzeug:</b> {escape(vehicle)}")
    addr_lines = _get_customer_address_lines(quote) or [_get_customer_name(quote)]
    addr = "<b>Kunde:</b><br/>" + "<br/>".join(escape(x) for x in addr_lines)
    meta_table = Table([[Paragraph("<br/>".join(meta), normal_sm), Paragraph(addr, normal_sm)]], colWidths=[85 * mm, 85 * mm])
    meta_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story += [meta_table, Spacer(1, 8 * mm)]

    # --- Positionen ---
    data = [[Paragraph(f"<b>{h}</b>", th) for h in ("Pos", "Beschreibung", "Menge", "Einheit", "Einzelpreis", "MwSt %", "Gesamt netto")]]
    for it in quote.items:
        data.append([
            str(it.position), Paragraph(escape(it.description), cell), _fmt_qty(it.quantity), it.unit or "Stk",
            _fmt_eur(it.unit_price), _fmt_rate(it.vat_rate), _fmt_eur(it.line_total_net),
        ])
    n = len(data)
    t = Table(data, colWidths=[12 * mm, 55 * mm, 15 * mm, 18 * mm, 25 * mm, 18 * mm, 27 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ("TOPPADDING", (0, 0), (-1, 0), 6), ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TOPPADDING", (0, 1), (-1, -1), 5), ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _ROW_ALT]),
        ("BOX", (0, 0), (-1, -1), 0.6, _BORDER), ("LINEBELOW", (0, 0), (-1, 0), 0.6, _BORDER),
        ("INNERGRID", (0, 1), (-1, -1), 0.4, _BORDER),
        ("ALIGN", (2, 1), (2, n), "RIGHT"), ("ALIGN", (4, 1), (-1, n), "RIGHT"),
    ]))
    story += [t, Spacer(1, 8 * mm)]

    # --- Summen (MwSt je Steuersatz) ---
    breakdown = _vat_breakdown(quote.items)
    sums = [["Netto:", _fmt_eur(quote.net_amount)]]
    for rate, basis, tax in breakdown:
        label = f"MwSt {_fmt_rate(rate)}" + (f" auf {_fmt_eur(basis)}" if len(breakdown) > 1 else "")
        sums.append([f"{label}:", _fmt_eur(tax)])
    sums.append(["Gesamtbetrag (brutto):", _fmt_eur(quote.gross_amount)])
    st = Table(sums, colWidths=[60 * mm, 30 * mm], hAlign="RIGHT")
    st.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9), ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE", (0, -1), (-1, -1), 1.0, colors.black), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(st)

    # --- Hinweise ---
    notes: list[str] = []
    if is_estimate:
        notes.append(ESTIMATE_NOTE)
    elif quote.valid_until:
        notes.append(f"Dieses Angebot ist gültig bis {quote.valid_until.strftime('%d.%m.%Y')}.")
    if any(rate == 0 for rate, _, _ in breakdown):
        notes.append(s.get("invoice_vat_exemption_note", "").strip() or _DEFAULT_EXEMPTION_NOTE)
    if quote.notes:
        notes.append(quote.notes)
    for note in notes:
        story += [Spacer(1, 4 * mm), Paragraph(escape(note).replace("\n", "<br/>"), normal_sm)]

    # --- Auftragserteilung (Unterschriftsfeld) ---
    sign = Table(
        [["", "", ""], ["Datum", "", "Unterschrift Auftraggeber"]],
        colWidths=[55 * mm, 15 * mm, 80 * mm], rowHeights=[12 * mm, None], hAlign="LEFT",
    )
    sign.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (0, 0), 0.6, colors.black), ("LINEBELOW", (2, 0), (2, 0), 0.6, colors.black),
        ("FONTSIZE", (0, 1), (-1, 1), 8), ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor("#555555")),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(KeepTogether([
        Spacer(1, 10 * mm),
        Paragraph(f"<b>Auftrag erteilt</b> – ich beauftrage die Ausführung gemäß diesem {title}.", normal_sm),
        sign,
    ]))

    doc.build(story)
    return buffer.getvalue()
