"""PDF für die Inventur: Zählliste (offen) bzw. Inventurliste mit Lagerwert (abgeschlossen)."""

from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.models.stock_count import StockCount
from app.services.pdf import _BORDER, _HEADER_BG, _ROW_ALT, _fmt_eur, _get_company_settings

_CENT = Decimal("0.01")


def _page_footer(title: str):
    """Fußzeile mit Seitenzahl (Zähllisten werden oft gestapelt ausgedruckt)."""
    def draw(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#555555"))
        canvas.drawString(15 * mm, 8 * mm, title)
        canvas.drawRightString(doc.pagesize[0] - 15 * mm, 8 * mm, f"Seite {doc.page}")
        canvas.restoreState()
    return draw


def generate_stock_count_pdf(db: Session, sc: StockCount) -> bytes:
    """Zählliste bzw. Inventurliste erzeugen."""
    completed = sc.status == "completed"
    title = "Inventurliste" if completed else "Zählliste"
    if sc.status == "cancelled":
        title = "Zählliste (abgebrochen)"

    buffer = BytesIO()
    page = landscape(A4)
    doc = SimpleDocTemplate(
        buffer, pagesize=page, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=14 * mm, bottomMargin=16 * mm,
        title=f"{title} {sc.count_number}",
    )
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    small = ParagraphStyle("Small", parent=normal, fontSize=8, leading=10)
    cell = ParagraphStyle("Cell", parent=normal, fontSize=8, leading=10)
    th = ParagraphStyle("Th", parent=normal, fontSize=8, leading=10, textColor=colors.white, fontName="Helvetica-Bold")
    company = _get_company_settings(db).get("company_name", "").strip() or "WareVision"

    story = [
        Paragraph(f"<b>{title} {escape(sc.count_number)}</b>", ParagraphStyle("T", parent=normal, fontSize=15, leading=19)),
        Spacer(1, 2 * mm),
        Paragraph(
            f"{escape(company)} · Stichtag: <b>{sc.count_date.strftime('%d.%m.%Y')}</b> · "
            f"Umfang: {escape(sc.scope_label or 'Gesamtes Lager')} · {len(sc.items)} Artikel",
            small,
        ),
    ]
    if sc.notes:
        story.append(Paragraph(f"Hinweis: {escape(sc.notes)}", small))
    if completed and sc.completed_at:
        story.append(Paragraph(f"Abgeschlossen am {sc.completed_at.astimezone().strftime('%d.%m.%Y %H:%M')}", small))
    story.append(Spacer(1, 4 * mm))

    if completed:
        headers = ["Nr.", "Artikelnr.", "Bezeichnung", "Lagerort", "Soll", "Ist", "Diff.", "EK netto", "Wert Ist", "Bemerkung"]
        widths = [10, 30, 72, 38, 14, 16, 14, 22, 24, 27]
    else:
        # Blindzählung: ohne Soll-Menge, damit nicht abgeschrieben, sondern wirklich gezählt wird
        headers = ["Nr.", "Artikelnr.", "Bezeichnung", "Lagerort", "Ist (gezählt)", "Bemerkung"]
        widths = [10, 32, 95, 50, 30, 50]
    data = [[Paragraph(h, th) for h in headers]]
    for n, i in enumerate(sc.items, 1):
        base = [str(n), Paragraph(escape(i.article_number), cell), Paragraph(escape(i.article_name), cell),
                Paragraph(escape(i.location or ""), cell)]
        if completed:
            value = (i.unit_cost * i.counted_qty).quantize(_CENT)
            diff = i.difference or 0
            data.append(base + [
                str(i.expected_qty), str(i.counted_qty), f"+{diff}" if diff > 0 else str(diff),
                _fmt_eur(i.unit_cost), _fmt_eur(value), Paragraph(escape(i.note or ""), cell),
            ])
        else:
            data.append(base + [
                "" if i.counted_qty is None else str(i.counted_qty),  # leer = per Hand eintragen
                Paragraph(escape(i.note or ""), cell),
            ])
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _ROW_ALT]),
        ("BOX", (0, 0), (-1, -1), 0.6, _BORDER), ("INNERGRID", (0, 0), (-1, -1), 0.4, _BORDER),
    ]
    if completed:
        style.append(("ALIGN", (4, 1), (8, -1), "RIGHT"))
        for row, i in enumerate(sc.items, 1):
            if i.difference:
                style.append(("TEXTCOLOR", (6, row), (6, row), colors.HexColor("#b91c1c" if i.difference < 0 else "#15803d")))
    else:
        # Ist-Spalte hervorheben und Zeilen höher für handschriftliche Einträge
        style += [("BACKGROUND", (4, 1), (4, -1), colors.HexColor("#fff8dc")), ("ALIGN", (4, 1), (4, -1), "RIGHT"),
                  ("TOPPADDING", (0, 1), (-1, -1), 6), ("BOTTOMPADDING", (0, 1), (-1, -1), 6)]
    t.setStyle(TableStyle(style))
    story.append(t)

    if completed:
        diffs = [i for i in sc.items if i.difference]
        sums = Table([
            ["Lagerwert laut Buchbestand (EK netto):", _fmt_eur(sc.value_expected or 0)],
            ["Lagerwert laut Inventur (EK netto):", _fmt_eur(sc.value_counted or 0)],
            ["Inventurdifferenz:", _fmt_eur((sc.value_counted or 0) - (sc.value_expected or 0))],
            ["Positionen mit Differenz:", str(len(diffs))],
        ], colWidths=[75 * mm, 35 * mm], hAlign="RIGHT")
        sums.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9), ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
            ("LINEABOVE", (0, 1), (-1, 1), 0.8, colors.black),
        ]))
        story += [Spacer(1, 5 * mm), sums]

    # Unterschriften: wer hat gezählt, wer hat geprüft (Nachweis der körperlichen Bestandsaufnahme)
    sign = Table(
        [["", "", "", "", ""], ["Datum, Unterschrift Zähler/in", "", "Datum, Unterschrift Kontrolle", "", "Name in Druckbuchstaben"]],
        colWidths=[75 * mm, 12 * mm, 75 * mm, 12 * mm, 70 * mm], rowHeights=[12 * mm, None], hAlign="LEFT",
    )
    sign.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (0, 0), 0.6, colors.black), ("LINEBELOW", (2, 0), (2, 0), 0.6, colors.black),
        ("LINEBELOW", (4, 0), (4, 0), 0.6, colors.black),
        ("FONTSIZE", (0, 1), (-1, 1), 7), ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor("#555555")),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(KeepTogether([Spacer(1, 10 * mm), sign]))

    footer = _page_footer(f"{title} {sc.count_number} · Stichtag {sc.count_date.strftime('%d.%m.%Y')}")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
