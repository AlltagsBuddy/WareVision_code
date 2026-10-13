"""PDF-Generierung fuer Rechnungen und Werkstattauftraege."""

import os
from datetime import date
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, HRFlowable

from app.models.app_setting import AppSetting
from app.models.invoice import Invoice
from app.models.workshop_order import WorkshopOrder
from app.services.pdfa import register_embedded_fonts
from sqlalchemy.orm import Session

# Schriften einbetten (PDF/A-3 für ZUGFeRD); ohne Schriftdateien bleibt Helvetica aktiv
register_embedded_fonts()

_CENT = Decimal("0.01")
_DEFAULT_EXEMPTION_NOTE = "Positionen mit 0 % MwSt sind von der Umsatzsteuer befreit."


def _fmt_num(value: Decimal | float, decimals: int = 2) -> str:
    """Zahl im deutschen Format (1.234,56)."""
    s = f"{Decimal(value):,.{decimals}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_eur(value: Decimal | float) -> str:
    """Betrag im deutschen Format mit Euro-Zeichen."""
    return f"{_fmt_num(value)} \u20ac"


def _fmt_qty(value: Decimal | float) -> str:
    """Menge ohne überflüssige Nullen im deutschen Format (2 / 2,1 / 0,25)."""
    s = f"{Decimal(value).normalize():f}"
    return s.replace(".", ",")


def _fmt_rate(value: Decimal | float) -> str:
    """Steuersatz ohne überflüssige Nullen (19 % / 7 %)."""
    return f"{_fmt_qty(Decimal(value).quantize(_CENT))} %"


def _vat_breakdown(items) -> list[tuple[Decimal, Decimal, Decimal]]:
    """Steueraufschlüsselung je Steuersatz: [(Satz, Netto-Basis, Steuerbetrag)].
    Gleiche Rechenweise wie in der E-Rechnung (je Satz kaufmännisch gerundet)."""
    from decimal import ROUND_HALF_UP

    bases: dict[Decimal, Decimal] = {}
    for it in items:
        rate = Decimal(it.vat_rate).quantize(_CENT)
        bases[rate] = bases.get(rate, Decimal("0")) + Decimal(it.line_total_net).quantize(_CENT, rounding=ROUND_HALF_UP)
    return [
        (rate, basis, (basis * rate / 100).quantize(_CENT, rounding=ROUND_HALF_UP))
        for rate, basis in sorted(bases.items(), reverse=True)
    ]

# Akzentfarbe fuer Tabellenkoepfe (dezentes Blaugrau)
_HEADER_BG = colors.HexColor("#2c3e50")
_ROW_ALT = colors.HexColor("#f7f9fc")
_BORDER = colors.HexColor("#d0d7de")


def _get_company_settings(db: Session) -> dict[str, str]:
    """Get company settings for PDF header."""
    keys = (
        "company_name",
        "company_address",
        "company_vat_id",
        "company_email",
        "company_phone",
        "company_website",
        "company_bank_name",
        "company_bank_iban",
        "company_bank_bic",
        "company_bank_account_holder",
        "company_logo_path",
        "invoice_vat_exemption_note",
    )
    rows = db.query(AppSetting).filter(AppSetting.key.in_(keys)).all()
    return {r.key: r.value or "" for r in rows}


def _get_customer_name(inv: Invoice) -> str:
    """Get customer display name."""
    c = inv.customer
    if c.company_name:
        return c.company_name
    parts = [c.first_name or "", c.last_name or ""]
    return " ".join(parts).strip() or (c.email or "–")


def _get_customer_address_lines(inv: Invoice) -> list[str]:
    """Rechnungsadresse des Kunden als Zeilenliste."""
    c = inv.customer
    lines: list[str] = []

    # Firmenname bei B2B
    if c.company_name:
        lines.append(c.company_name)
        # Ansprechpartner darunter wenn vorhanden
        contact = " ".join(filter(None, [c.first_name, c.last_name])).strip()
        if contact:
            lines.append(contact)
    else:
        salutation = c.salutation or ""
        name = " ".join(filter(None, [salutation, c.first_name, c.last_name])).strip()
        if name:
            lines.append(name)

    # Adresse: bevorzugt billing, dann main
    addr = None
    if hasattr(c, "addresses") and c.addresses:
        for a in c.addresses:
            if a.address_type == "billing":
                addr = a
                break
        if not addr:
            for a in c.addresses:
                if a.address_type == "main":
                    addr = a
                    break
        if not addr:
            addr = c.addresses[0]

    if addr:
        street_line = addr.street
        if addr.house_number:
            street_line += f" {addr.house_number}"
        lines.append(street_line)
        city_line = f"{addr.postal_code} {addr.city}"
        lines.append(city_line)
        if addr.country and addr.country.lower() not in ("deutschland", "germany", "de"):
            lines.append(addr.country)

    return lines


def _build_logo_cell(logo_path: str, max_height: float = 20 * mm) -> Image | None:
    """Logo-Bild laden wenn Pfad existiert, sonst None."""
    if not logo_path:
        return None
    if not os.path.isfile(logo_path):
        return None
    try:
        img = Image(logo_path)
        # Proportional skalieren auf max_height
        ratio = img.imageWidth / img.imageHeight
        img._restrictSize(ratio * max_height, max_height)
        return img
    except Exception:
        return None


def generate_invoice_pdf(db: Session, inv: Invoice) -> bytes:
    """Rechnung als PDF generieren, gibt Bytes zurueck."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
    )
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    small = ParagraphStyle("Small", parent=normal, fontSize=8, leading=11)
    normal_sm = ParagraphStyle("NormalSm", parent=normal, fontSize=9, leading=13)
    bold_sm = ParagraphStyle("BoldSm", parent=normal, fontSize=9, leading=13, fontName="Helvetica-Bold")
    story = []

    settings_dict = _get_company_settings(db)
    company_name = settings_dict.get("company_name", "").strip() or "WareVision"
    company_address = settings_dict.get("company_address", "").strip()
    company_vat = settings_dict.get("company_vat_id", "").strip()
    company_email = settings_dict.get("company_email", "").strip()
    company_phone = settings_dict.get("company_phone", "").strip()
    company_website = settings_dict.get("company_website", "").strip()
    company_bank_name = settings_dict.get("company_bank_name", "").strip()
    company_bank_iban = settings_dict.get("company_bank_iban", "").strip()
    company_bank_bic = settings_dict.get("company_bank_bic", "").strip()
    company_bank_holder = settings_dict.get("company_bank_account_holder", "").strip() or company_name
    logo_path = settings_dict.get("company_logo_path", "").strip()

    # --- Kopfzeile: Firmendaten links | Logo rechts ---
    logo_img = _build_logo_cell(logo_path, max_height=22 * mm)

    # Firmeninfo-Absatz links
    company_lines: list[str] = [f"<b>{company_name}</b>"]
    if company_address:
        for line in company_address.replace("\r\n", "\n").split("\n"):
            if line.strip():
                company_lines.append(line.strip())
    if company_email:
        company_lines.append(f"E-Mail: {company_email}")
    if company_phone:
        company_lines.append(f"Tel.: {company_phone}")
    if company_website:
        company_lines.append(f"Web: {company_website}")
    if company_vat:
        company_lines.append(f"USt-IdNr.: {company_vat}")

    company_para = Paragraph("<br/>".join(company_lines), small)

    if logo_img:
        header_data = [[company_para, logo_img]]
        header_table = Table(header_data, colWidths=[120 * mm, 50 * mm])
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ]))
    else:
        header_data = [[company_para]]
        header_table = Table(header_data, colWidths=[170 * mm])
        header_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))

    story.append(header_table)
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=_HEADER_BG))
    story.append(Spacer(1, 6 * mm))

    # --- Rechnungstitel ---
    story.append(Paragraph("<b>Rechnung</b>", ParagraphStyle(
        "InvoiceTitle", parent=normal, fontSize=18, leading=22, fontName="Helvetica-Bold",
    )))
    story.append(Spacer(1, 6 * mm))

    # --- Meta + Rechnungsadresse nebeneinander ---
    inv_lines = [
        f"<b>Rechnungsnummer:</b> {inv.invoice_number}",
        f"<b>Datum:</b> {inv.invoice_date.strftime('%d.%m.%Y')}",
    ]
    # Leistungsdatum (Pflichtangabe nach § 14 Abs. 4 Nr. 6 UStG)
    if inv.service_date:
        inv_lines.append(f"<b>Leistungsdatum:</b> {inv.service_date.strftime('%d.%m.%Y')}")
    if inv.due_date:
        inv_lines.append(f"<b>Fällig:</b> {inv.due_date.strftime('%d.%m.%Y')}")
    meta_para = Paragraph("<br/>".join(inv_lines), normal_sm)

    # Rechnungsadresse
    addr_lines = _get_customer_address_lines(inv)
    if addr_lines:
        addr_text = "<b>Rechnungsadresse:</b><br/>" + "<br/>".join(addr_lines)
    else:
        addr_text = f"<b>Rechnungsadresse:</b><br/>{_get_customer_name(inv)}"
    addr_para = Paragraph(addr_text, normal_sm)

    meta_table = Table([[meta_para, addr_para]], colWidths=[85 * mm, 85 * mm])
    meta_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 8 * mm))

    # --- Positionstabelle ---
    data = [[
        Paragraph("<b>Pos</b>", ParagraphStyle("Th", parent=normal, fontSize=9, textColor=colors.white, fontName="Helvetica-Bold")),
        Paragraph("<b>Beschreibung</b>", ParagraphStyle("Th", parent=normal, fontSize=9, textColor=colors.white, fontName="Helvetica-Bold")),
        Paragraph("<b>Menge</b>", ParagraphStyle("Th", parent=normal, fontSize=9, textColor=colors.white, fontName="Helvetica-Bold")),
        Paragraph("<b>Einheit</b>", ParagraphStyle("Th", parent=normal, fontSize=9, textColor=colors.white, fontName="Helvetica-Bold")),
        Paragraph("<b>Einzelpreis</b>", ParagraphStyle("Th", parent=normal, fontSize=9, textColor=colors.white, fontName="Helvetica-Bold")),
        Paragraph("<b>MwSt %</b>", ParagraphStyle("Th", parent=normal, fontSize=9, textColor=colors.white, fontName="Helvetica-Bold")),
        Paragraph("<b>Gesamt netto</b>", ParagraphStyle("Th", parent=normal, fontSize=9, textColor=colors.white, fontName="Helvetica-Bold")),
    ]]
    cell_style = ParagraphStyle("Cell", parent=normal, fontSize=9, leading=11)
    for i, item in enumerate(inv.items, 1):
        data.append([
            str(i),
            # Vollständige Leistungsbeschreibung (Pflichtangabe), mit Zeilenumbruch
            Paragraph(escape(item.description or ""), cell_style),
            _fmt_qty(item.quantity),
            item.unit or "Stk",
            _fmt_eur(item.unit_price),
            _fmt_rate(item.vat_rate),
            _fmt_eur(item.line_total_net),
        ])

    # Summe der Spaltenbreiten = 170 mm (A4 minus 2 × 20 mm Rand)
    t = Table(
        data,
        colWidths=[12 * mm, 55 * mm, 15 * mm, 18 * mm, 25 * mm, 18 * mm, 27 * mm],
        repeatRows=1,
    )
    row_count = len(data)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        # Kopfzeile
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        # Datenzeilen
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _ROW_ALT]),
        # Rahmen
        ("BOX", (0, 0), (-1, -1), 0.6, _BORDER),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, _BORDER),
        ("INNERGRID", (0, 1), (-1, -1), 0.4, _BORDER),
        # Ausrichtung
        ("ALIGN", (2, 1), (2, row_count), "RIGHT"),
        ("ALIGN", (4, 0), (-1, row_count), "RIGHT"),
    ]))
    story.append(t)
    story.append(Spacer(1, 8 * mm))

    # --- Summen-Block: Steuer je Steuersatz (§ 14 Abs. 4 Nr. 8 UStG) ---
    breakdown = _vat_breakdown(inv.items)
    sum_data = [["Netto:", _fmt_eur(inv.net_amount)]]
    for rate, basis, tax in breakdown:
        label = f"MwSt {_fmt_rate(rate)}"
        if len(breakdown) > 1:
            label += f" auf {_fmt_eur(basis)}"
        sum_data.append([f"{label}:", _fmt_eur(tax)])
    sum_data.append(["Brutto (Gesamtbetrag):", _fmt_eur(inv.gross_amount)])
    sum_table = Table(sum_data, colWidths=[60 * mm, 30 * mm], hAlign="RIGHT")
    sum_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE", (0, -1), (-1, -1), 1.0, colors.black),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(sum_table)

    # --- Bankverbindung ---
    if company_bank_name or company_bank_iban or company_bank_bic:
        story.append(Spacer(1, 8 * mm))
        bank_lines = ["<b>Bankverbindung:</b>"]
        if company_bank_holder:
            bank_lines.append(f"Kontoinhaber: {company_bank_holder}")
        if company_bank_name:
            bank_lines.append(f"Bank: {company_bank_name}")
        if company_bank_iban:
            bank_lines.append(f"IBAN: {company_bank_iban}")
        if company_bank_bic:
            bank_lines.append(f"BIC: {company_bank_bic}")
        story.append(Paragraph("<br/>".join(bank_lines), normal_sm))

    # --- Hinweis Steuerbefreiung bei 0-%-Positionen (§ 14 Abs. 4 Nr. 8 UStG) ---
    if any(rate == 0 for rate, _, _ in breakdown):
        note = settings_dict.get("invoice_vat_exemption_note", "").strip() or _DEFAULT_EXEMPTION_NOTE
        story.append(Spacer(1, 5 * mm))
        story.append(Paragraph(f"<b>Hinweis:</b> {escape(note)}", normal_sm))

    # --- Anmerkungen ---
    if inv.notes:
        story.append(Spacer(1, 5 * mm))
        story.append(Paragraph(f"<b>Anmerkungen:</b> {escape(inv.notes)}", normal_sm))

    doc.build(story)
    return buffer.getvalue()


def generate_workshop_order_pdf(db: Session, order: WorkshopOrder) -> bytes:
    """Werkstattauftrag als druckbares PDF generieren (Abhak-Liste fuer Mechaniker)."""
    from datetime import datetime, timezone

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    bold = ParagraphStyle("Bold", parent=normal, fontName="Helvetica-Bold")
    small = ParagraphStyle("Small", parent=normal, fontSize=8)
    heading = styles["Heading2"]

    settings_dict = _get_company_settings(db)
    company_name = settings_dict.get("company_name", "").strip() or "WareVision"
    company_address = settings_dict.get("company_address", "").strip()
    company_email = settings_dict.get("company_email", "").strip()
    company_phone = settings_dict.get("company_phone", "").strip()
    logo_path = settings_dict.get("company_logo_path", "").strip()

    story = []

    # --- Kopfzeile: Firma links | Logo rechts oben ---
    logo_img = _build_logo_cell(logo_path, max_height=20 * mm)

    wo_title = Paragraph("<b>Werkstattauftrag</b>", styles["Heading1"])
    company_para = Paragraph(f"<b>{company_name}</b>", normal)

    if logo_img:
        # Drei Spalten: Firmenname | Titel | Logo
        header_data = [[company_para, wo_title, logo_img]]
        header_table = Table(header_data, colWidths=[60 * mm, 70 * mm, 44 * mm])
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "CENTER"),
            ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ]))
    else:
        header_data = [[company_para, wo_title]]
        header_table = Table(header_data, colWidths=[90 * mm, 90 * mm])
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ]))
    story.append(header_table)

    if company_address or company_email or company_phone:
        contact_parts = []
        if company_address:
            contact_parts.append(company_address.replace("\n", " | "))
        if company_phone:
            contact_parts.append(f"Tel. {company_phone}")
        if company_email:
            contact_parts.append(company_email)
        story.append(Paragraph(" | ".join(contact_parts), small))

    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.black))
    story.append(Spacer(1, 4 * mm))

    # --- Auftragsinfo ---
    created = order.created_at.strftime("%d.%m.%Y") if order.created_at else "–"
    status_labels = {
        "new": "Neu", "planned": "Geplant", "in_progress": "In Arbeit",
        "completed": "Abgeschlossen", "invoiced": "Abgerechnet", "cancelled": "Storniert",
    }
    status_text = status_labels.get(order.status, order.status)

    info_data = [
        [Paragraph("<b>Auftragsnummer:</b>", normal), Paragraph(order.order_number or "–", normal),
         Paragraph("<b>Datum:</b>", normal), Paragraph(created, normal)],
        [Paragraph("<b>Status:</b>", normal), Paragraph(status_text, normal),
         Paragraph("<b>Erstellt:</b>", normal), Paragraph(created, normal)],
    ]
    if order.mileage_at_checkin:
        info_data.append([
            Paragraph("<b>Kilometerstand:</b>", normal),
            Paragraph(f"{order.mileage_at_checkin:,} km".replace(",", "."), normal),
            Paragraph("", normal), Paragraph("", normal),
        ])

    info_table = Table(info_data, colWidths=[45 * mm, 50 * mm, 35 * mm, 50 * mm])
    info_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 4 * mm))

    # --- Kunde & Fahrzeug ---
    customer = order.customer
    vehicle = order.vehicle

    cust_name = "–"
    if customer:
        if customer.company_name:
            cust_name = customer.company_name
            if customer.first_name or customer.last_name:
                cust_name += f" / {(customer.first_name or '')} {(customer.last_name or '')}".strip()
        else:
            cust_name = f"{customer.first_name or ''} {customer.last_name or ''}".strip() or (customer.email or "–")

    veh_parts = []
    if vehicle:
        if vehicle.license_plate:
            veh_parts.append(vehicle.license_plate)
        if vehicle.vin:
            veh_parts.append(f"FIN: {vehicle.vin}")
        if vehicle.build_year:
            veh_parts.append(str(vehicle.build_year))
        if vehicle.color:
            veh_parts.append(vehicle.color)
    veh_text = " | ".join(veh_parts) if veh_parts else "–"

    cv_data = [
        [Paragraph("<b>Kunde:</b>", normal), Paragraph(cust_name, normal)],
        [Paragraph("<b>Fahrzeug:</b>", normal), Paragraph(veh_text, normal)],
    ]
    if customer and customer.phone:
        cv_data.append([Paragraph("<b>Telefon:</b>", normal), Paragraph(customer.phone, normal)])

    cv_table = Table(cv_data, colWidths=[35 * mm, 145 * mm])
    cv_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5f5f5")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(cv_table)
    story.append(Spacer(1, 4 * mm))

    # --- Kundenbeschreibung ---
    if order.complaint_description:
        story.append(Paragraph("<b>Kundenbeschreibung / Anliegen:</b>", bold))
        story.append(Paragraph(order.complaint_description, normal))
        story.append(Spacer(1, 3 * mm))

    # --- Positionen mit Abhak-Kaestchen ---
    story.append(Paragraph("<b>Auftragspositionen</b>", heading))

    item_type_labels = {"labor": "Arbeit", "material": "Teile", "service": "Service"}
    pos_data = [["", "Typ", "Beschreibung", "Menge", "Einheit", "Einzelpreis", "Gesamt"]]
    total = Decimal("0")
    for item in order.items:
        qty = Decimal(str(item.quantity or 0))
        price = Decimal(str(item.unit_price or 0))
        line_total = qty * price
        total += line_total
        pos_data.append([
            "[ ]",
            item_type_labels.get(item.item_type, item.item_type),
            item.description[:55] + ("…" if len(item.description) > 55 else ""),
            str(qty.normalize()),
            item.unit or "",
            f"{price:.2f} EUR",
            f"{line_total:.2f} EUR",
        ])

    pos_data.append(["", "", "", "", "", Paragraph("<b>Gesamt:</b>", normal), Paragraph(f"<b>{total:.2f} EUR</b>", normal)])

    col_widths = [8 * mm, 18 * mm, 68 * mm, 16 * mm, 16 * mm, 26 * mm, 26 * mm]
    pos_table = Table(pos_data, colWidths=col_widths, repeatRows=1)
    pos_table.setStyle(TableStyle([
        # Kopfzeile
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        # Datenzeilen
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f9f9f9")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        # Summenzeile
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
    ]))
    story.append(pos_table)
    story.append(Spacer(1, 5 * mm))

    # --- Interne Notizen ---
    if order.internal_notes:
        story.append(Paragraph("<b>Interne Notizen:</b>", bold))
        story.append(Paragraph(order.internal_notes, normal))
        story.append(Spacer(1, 4 * mm))

    # --- Unterschriften ---
    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Spacer(1, 4 * mm))

    sig_data = [[
        Paragraph("Datum: ___________________", small),
        Paragraph("Mechaniker: ___________________", small),
        Paragraph("Unterschrift Kunde: ___________________", small),
    ]]
    sig_table = Table(sig_data, colWidths=[60 * mm, 60 * mm, 60 * mm])
    sig_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(sig_table)

    doc.build(story)
    return buffer.getvalue()


def generate_dsgvo_consent_pdf(
    db: Session,
    customer,
    signature_bytes: bytes | None = None,
) -> bytes:
    """DSGVO-Einwilligungs-PDF fuer einen Kunden generieren.
    Wenn signature_bytes uebergeben wird, wird die Unterschrift ins PDF eingebettet."""
    from datetime import date

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
    )
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    small = ParagraphStyle("DSmall", parent=normal, fontSize=8, leading=12)
    normal_sm = ParagraphStyle("DNormalSm", parent=normal, fontSize=9, leading=13)
    bold_sm = ParagraphStyle("DBoldSm", parent=normal, fontSize=9, leading=13, fontName="Helvetica-Bold")
    h2 = ParagraphStyle("DH2", parent=normal, fontSize=11, leading=15, fontName="Helvetica-Bold", spaceAfter=4)
    h1_style = ParagraphStyle("DH1", parent=normal, fontSize=15, leading=20, fontName="Helvetica-Bold", spaceAfter=6)

    settings_dict = _get_company_settings(db)
    company_name = settings_dict.get("company_name", "").strip() or "WareVision"
    company_address = settings_dict.get("company_address", "").strip()
    company_email = settings_dict.get("company_email", "").strip()
    company_phone = settings_dict.get("company_phone", "").strip()
    logo_path = settings_dict.get("company_logo_path", "").strip()

    story = []

    # --- Kopfzeile: Firma links | Logo rechts ---
    logo_img = _build_logo_cell(logo_path, max_height=20 * mm)
    company_lines = [f"<b>{company_name}</b>"]
    if company_address:
        for ln in company_address.replace("\r\n", "\n").split("\n"):
            if ln.strip():
                company_lines.append(ln.strip())
    if company_email:
        company_lines.append(f"E-Mail: {company_email}")
    if company_phone:
        company_lines.append(f"Tel.: {company_phone}")
    company_para = Paragraph("<br/>".join(company_lines), small)

    if logo_img:
        hdr = Table([[company_para, logo_img]], colWidths=[130 * mm, 40 * mm])
        hdr.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (1, 0), (1, 0), "RIGHT")]))
    else:
        hdr = Table([[company_para]], colWidths=[170 * mm])
        hdr.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(hdr)
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=_HEADER_BG))
    story.append(Spacer(1, 5 * mm))

    # --- Titel ---
    story.append(Paragraph("Einwilligung zur Verarbeitung personenbezogener Daten", h1_style))
    story.append(Paragraph("gem\u00e4\u00df Art. 6 Abs. 1 lit. a und Art. 7 DSGVO", normal_sm))
    story.append(Spacer(1, 5 * mm))

    # --- Betroffene Person & Datum ---
    cust = customer
    cust_name_parts = []
    if cust.company_name:
        cust_name_parts.append(cust.company_name)
    name = " ".join(filter(None, [cust.salutation or "", cust.first_name or "", cust.last_name or ""])).strip()
    if name:
        cust_name_parts.append(name)
    cust_display = ", ".join(cust_name_parts) if cust_name_parts else "–"

    addr_line = ""
    if hasattr(cust, "addresses") and cust.addresses:
        addr = next((a for a in cust.addresses if a.address_type in ("billing", "main")), cust.addresses[0] if cust.addresses else None)
        if addr:
            hn = f" {addr.house_number}" if addr.house_number else ""
            addr_line = f"{addr.street}{hn}, {addr.postal_code} {addr.city}"

    person_rows = [
        [Paragraph("<b>Betroffene Person:</b>", bold_sm), Paragraph(cust_display, normal_sm)],
        [Paragraph("<b>Anschrift:</b>", bold_sm), Paragraph(addr_line or "–", normal_sm)],
    ]
    if cust.email:
        person_rows.append([Paragraph("<b>E-Mail:</b>", bold_sm), Paragraph(cust.email, normal_sm)])
    if cust.phone:
        person_rows.append([Paragraph("<b>Telefon:</b>", bold_sm), Paragraph(cust.phone, normal_sm)])
    person_rows.append([Paragraph("<b>Datum:</b>", bold_sm), Paragraph(date.today().strftime("%d.%m.%Y"), normal_sm)])

    person_table = Table(person_rows, colWidths=[45 * mm, 125 * mm])
    person_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7f9fc")),
        ("BOX", (0, 0), (-1, -1), 0.5, _BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, _BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(person_table)
    story.append(Spacer(1, 6 * mm))

    # --- Abschnitte ---
    sections = [
        (
            "1. Verantwortlicher",
            (
                "Verantwortlicher f\u00fcr die Verarbeitung Ihrer personenbezogenen Daten ist:<br/>"
                f"<b>{company_name}</b>"
                + (f"<br/>{company_address.replace(chr(10), ', ')}" if company_address else "")
                + (f"<br/>E-Mail: {company_email}" if company_email else "")
                + (f"<br/>Tel.: {company_phone}" if company_phone else "")
            ),
        ),
        (
            "2. Verarbeitete Daten",
            (
                "Wir verarbeiten folgende personenbezogene Daten:<br/>"
                "&#8226; Stammdaten: Name, Anschrift, Kontaktdaten (E-Mail, Telefon)<br/>"
                "&#8226; Fahrzeugdaten: Kennzeichen, FIN, Kilometerstand, Baujahr<br/>"
                "&#8226; Werkstattdaten: Auftr\u00e4ge, Reparaturen, Wartungshistorie<br/>"
                "&#8226; Rechnungs- und Zahlungsdaten gem\u00e4\u00df GoBD"
            ),
        ),
        (
            "3. Zweck der Verarbeitung",
            (
                "Ihre Daten werden verarbeitet f\u00fcr:<br/>"
                "&#8226; Erf\u00fcllung des Werkstattvertrags (Reparatur, Wartung, Service)<br/>"
                "&#8226; Rechnungsstellung, Buchhaltung und gesetzliche Aufbewahrung<br/>"
                "&#8226; Kommunikation \u00fcber Reparaturstatus und Terminvereinbarungen<br/>"
                "&#8226; Kundenverwaltung und Qualit\u00e4tssicherung"
            ),
        ),
        (
            "4. Rechtsgrundlage",
            (
                "&#8226; <b>Art. 6 Abs. 1 lit. b DSGVO</b> \u2013 Vertragsanbahnung und -erf\u00fcllung<br/>"
                "&#8226; <b>Art. 6 Abs. 1 lit. a DSGVO</b> \u2013 Ihre Einwilligung f\u00fcr weiterf\u00fchrende Kommunikation<br/>"
                "&#8226; <b>Art. 6 Abs. 1 lit. c DSGVO</b> \u2013 Gesetzliche Verpflichtungen (GoBD, Steuerrecht)"
            ),
        ),
        (
            "5. Speicherdauer",
            (
                "Daten werden gespeichert solange die Gesch\u00e4ftsbeziehung besteht. "
                "Rechnungsunterlagen werden gem\u00e4\u00df \u00a7\u202f147 AO mindestens 10 Jahre aufbewahrt. "
                "Nach Ablauf der Fristen erfolgt L\u00f6schung oder Anonymisierung."
            ),
        ),
        (
            "6. Weitergabe an Dritte",
            (
                "Eine Weitergabe erfolgt nur:<br/>"
                "&#8226; Im gesetzlich vorgeschriebenen Umfang (z.\u202fB. Steuerberater, Finanzamt)<br/>"
                "&#8226; An Auftragsverarbeiter gem\u00e4\u00df Art.\u202f28 DSGVO (z.\u202fB. IT-Dienstleister)<br/>"
                "&#8226; Mit Ihrer ausdr\u00fccklichen Einwilligung"
            ),
        ),
        (
            "7. Ihre Rechte",
            (
                "Sie haben folgende Rechte:<br/>"
                "&#8226; <b>Auskunft</b> (Art. 15) \u2013 Kopie Ihrer gespeicherten Daten<br/>"
                "&#8226; <b>Berichtigung</b> (Art. 16) \u2013 Korrektur unrichtiger Daten<br/>"
                "&#8226; <b>L\u00f6schung</b> (Art. 17) \u2013 L\u00f6schung bei Wegfall des Verarbeitungsgrunds<br/>"
                "&#8226; <b>Einschr\u00e4nkung</b> (Art. 18) \u2013 Einschr\u00e4nkung der Verarbeitung<br/>"
                "&#8226; <b>Daten\u00fcbertragbarkeit</b> (Art. 20) \u2013 Daten in maschinenlesbarem Format<br/>"
                "&#8226; <b>Widerspruch</b> (Art. 21) \u2013 Widerspruch gegen die Verarbeitung<br/>"
                "&#8226; <b>Beschwerde</b> (Art. 77) \u2013 Beschwerde bei der zust\u00e4ndigen Aufsichtsbeh\u00f6rde"
            ),
        ),
        (
            "8. Widerruf der Einwilligung",
            (
                "Sie k\u00f6nnen Ihre Einwilligung jederzeit formlos widerrufen (per E-Mail oder schriftlich). "
                "Der Widerruf ber\u00fchrt nicht die Rechtm\u00e4\u00dfigkeit der bis dahin erfolgten Verarbeitung. "
                "Verarbeitungen auf Basis gesetzlicher Pflichten bleiben unber\u00fchrt."
            ),
        ),
    ]

    for title, text in sections:
        story.append(Paragraph(title, h2))
        story.append(Paragraph(text, normal_sm))
        story.append(Spacer(1, 4 * mm))

    # --- Einwilligungserklaerung ---
    story.append(HRFlowable(width="100%", thickness=0.8, color=_BORDER))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Einwilligungserkl\u00e4rung", h2))
    consent_text = (
        "Ich habe die vorstehenden Datenschutzinformationen vollst\u00e4ndig gelesen und verstanden. "
        "Ich willige in die Verarbeitung meiner personenbezogenen Daten durch <b>{company}</b> "
        "zu den unter Ziffer 3 genannten Zwecken ein. "
        "Mir ist bekannt, dass ich diese Einwilligung jederzeit mit Wirkung f\u00fcr die Zukunft widerrufen kann."
    ).format(company=company_name)
    story.append(Paragraph(consent_text, normal_sm))
    story.append(Spacer(1, 8 * mm))

    # --- Unterschriftenfeld ---
    if signature_bytes:
        sig_img_buf = BytesIO(signature_bytes)
        sig_img = Image(sig_img_buf, width=60 * mm, height=20 * mm)
        sig_row = Table(
            [[Paragraph("Ort, Datum: _________________________", small), sig_img]],
            colWidths=[85 * mm, 85 * mm],
        )
        sig_row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("ALIGN", (1, 0), (1, 0), "CENTER")]))
        story.append(sig_row)
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(
            f"Unterschrift des Kunden (digital signiert am {date.today().strftime('%d.%m.%Y')})",
            small,
        ))
    else:
        sig_row = Table(
            [[Paragraph("Ort, Datum: _________________________", small),
              Paragraph("Unterschrift Kunde: _________________________", small)]],
            colWidths=[85 * mm, 85 * mm],
        )
        sig_row.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9), ("TOPPADDING", (0, 0), (-1, -1), 4)]))
        story.append(sig_row)

    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        "Dieses Dokument wurde elektronisch erstellt gem\u00e4\u00df Art.\u202f13 DSGVO.",
        ParagraphStyle("DFooter", parent=normal, fontSize=7, textColor=colors.grey),
    ))

    doc.build(story)
    return buffer.getvalue()


def generate_reminder_pdf(db: Session, inv: Invoice) -> bytes:
    """Mahnbrief als PDF generieren. Mahnstufe wird aus inv.reminder_level gelesen."""
    from datetime import timedelta

    level = inv.reminder_level if inv.reminder_level > 0 else 1

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
    )
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    small = ParagraphStyle("RSmall", parent=normal, fontSize=8, leading=11)
    normal_sm = ParagraphStyle("RNormalSm", parent=normal, fontSize=9, leading=13)
    bold_sm = ParagraphStyle("RBoldSm", parent=normal, fontSize=9, leading=13, fontName="Helvetica-Bold")
    h1 = ParagraphStyle("RH1", parent=normal, fontSize=14, leading=18, fontName="Helvetica-Bold")
    story = []

    settings_dict = _get_company_settings(db)
    company_name = settings_dict.get("company_name", "").strip() or "WareVision"
    company_address = settings_dict.get("company_address", "").strip()
    company_email = settings_dict.get("company_email", "").strip()
    company_phone = settings_dict.get("company_phone", "").strip()
    company_vat = settings_dict.get("company_vat_id", "").strip()
    company_bank_name = settings_dict.get("company_bank_name", "").strip()
    company_bank_iban = settings_dict.get("company_bank_iban", "").strip()
    company_bank_bic = settings_dict.get("company_bank_bic", "").strip()
    company_bank_holder = settings_dict.get("company_bank_account_holder", "").strip() or company_name
    logo_path = settings_dict.get("company_logo_path", "").strip()

    logo_img = _build_logo_cell(logo_path, max_height=22 * mm)
    company_lines: list[str] = [f"<b>{company_name}</b>"]
    if company_address:
        for line in company_address.replace("\r\n", "\n").split("\n"):
            if line.strip():
                company_lines.append(line.strip())
    if company_email:
        company_lines.append(f"E-Mail: {company_email}")
    if company_phone:
        company_lines.append(f"Tel.: {company_phone}")
    if company_vat:
        company_lines.append(f"USt-IdNr.: {company_vat}")
    company_para = Paragraph("<br/>".join(company_lines), small)

    header_data = [[company_para, logo_img or ""]]
    header_table = Table(header_data, colWidths=[110 * mm, 60 * mm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=0.8, color=_HEADER_BG))
    story.append(Spacer(1, 6 * mm))

    # Empfaengeradresse
    addr_lines = _get_customer_address_lines(inv)
    for line in addr_lines:
        story.append(Paragraph(line, normal_sm))
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph(f"<para alignment='right'>{date.today().strftime('%d.%m.%Y')}</para>", normal_sm))
    story.append(Spacer(1, 6 * mm))

    subjects = {1: "Zahlungserinnerung", 2: "1. Mahnung", 3: "2. Mahnung"}
    subject = subjects.get(level, f"{level - 1}. Mahnung")
    story.append(Paragraph(f"{subject} zu Rechnung {inv.invoice_number}", h1))
    story.append(Spacer(1, 5 * mm))

    c = inv.customer
    if c.company_name:
        salutation_line = "Sehr geehrte Damen und Herren,"
    elif c.salutation and c.last_name:
        gender_map = {"Herr": "geehrter Herr", "Frau": "geehrte Frau"}
        g = gender_map.get(c.salutation, f"geehrte/r {c.salutation}")
        salutation_line = f"Sehr {g} {c.last_name},"
    else:
        salutation_line = "Sehr geehrte Damen und Herren,"
    story.append(Paragraph(salutation_line, normal_sm))
    story.append(Spacer(1, 4 * mm))

    intro_texts = {
        1: (
            "wir m\u00f6chten Sie freundlich daran erinnern, dass folgende Rechnung noch offen ist. "
            "M\u00f6glicherweise hat sich die Zahlung mit diesem Schreiben gekreuzt \u2013 in diesem Fall "
            "bitten wir Sie, dieses Schreiben als gegenstandslos zu betrachten."
        ),
        2: (
            "wir haben Ihnen bereits eine Zahlungserinnerung zugesandt, jedoch noch keinen Zahlungseingang "
            "verbuchen k\u00f6nnen. Wir bitten Sie dringend, den offenen Betrag umgehend zu begleichen."
        ),
        3: (
            "trotz unserer vorherigen Mahnungen ist die folgende Rechnung weiterhin offen. "
            "Wir fordern Sie hiermit letztmalig auf, den Betrag innerhalb der unten genannten Frist zu bezahlen. "
            "Andernfalls behalten wir uns vor, rechtliche Schritte einzuleiten."
        ),
    }
    story.append(Paragraph(intro_texts.get(level, intro_texts[3]), normal_sm))
    story.append(Spacer(1, 6 * mm))

    inv_date_str = inv.invoice_date.strftime("%d.%m.%Y") if inv.invoice_date else "–"
    orig_due_str = inv.due_date.strftime("%d.%m.%Y") if inv.due_date else "–"
    grace_days = {1: 14, 2: 10, 3: 7}
    new_due = date.today() + timedelta(days=grace_days.get(level, 7))
    new_due_str = new_due.strftime("%d.%m.%Y")
    gross_str = f"{inv.gross_amount:,.2f} \u20ac".replace(",", "X").replace(".", ",").replace("X", ".")

    detail_data = [
        ["Rechnungsnummer:", inv.invoice_number],
        ["Rechnungsdatum:", inv_date_str],
        ["Urspr\u00fcnglich f\u00e4llig:", orig_due_str],
        ["Offener Betrag:", gross_str],
        ["Neues Zahlungsziel:", new_due_str],
    ]
    detail_table = Table(detail_data, colWidths=[55 * mm, 115 * mm])
    detail_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, _ROW_ALT]),
    ]))
    story.append(detail_table)
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("Bitte \u00fcberweisen Sie den Betrag auf folgendes Konto:", normal_sm))
    story.append(Spacer(1, 3 * mm))
    bank_lines = []
    if company_bank_holder:
        bank_lines.append(f"Kontoinhaber: <b>{company_bank_holder}</b>")
    if company_bank_iban:
        bank_lines.append(f"IBAN: <b>{company_bank_iban}</b>")
    if company_bank_bic:
        bank_lines.append(f"BIC: {company_bank_bic}")
    if company_bank_name:
        bank_lines.append(f"Bank: {company_bank_name}")
    for bl in bank_lines:
        story.append(Paragraph(bl, normal_sm))
    if bank_lines:
        story.append(Spacer(1, 5 * mm))

    story.append(Paragraph(f"Verwendungszweck: {inv.invoice_number}", bold_sm))
    story.append(Spacer(1, 8 * mm))

    closing_texts = {
        1: "Vielen Dank f\u00fcr Ihre Aufmerksamkeit. Bei Fragen stehen wir Ihnen gerne zur Verf\u00fcgung.",
        2: "Sollten Sie bereits gezahlt haben, bitten wir Sie, dieses Schreiben als gegenstandslos zu betrachten und den Zahlungsnachweis an uns weiterzuleiten.",
        3: "Sollte die Zahlung nicht fristgerecht eingehen, werden wir die Forderung einem Inkassodienstleister \u00fcbergeben oder gerichtlich geltend machen.",
    }
    story.append(Paragraph(closing_texts.get(level, closing_texts[3]), normal_sm))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("Mit freundlichen Gr\u00fc\u00dfen", normal_sm))
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph(f"<b>{company_name}</b>", normal_sm))

    doc.build(story)
    return buffer.getvalue()
