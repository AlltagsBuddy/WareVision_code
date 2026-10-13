"""ZUGFeRD/Factur-X E-Rechnung (Profil EN16931) erzeugen und lesen.

Ausgang: XML nach EN 16931 (ZUGFeRD 2.x / Factur-X Profil EN16931, früher COMFORT),
eingebettet in die Rechnungs-PDF. Geprüft gegen Factur-X-XSD und EN16931-Schematron.
"""

import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from drafthorse.models.accounting import ApplicableTradeTax
from drafthorse.models.document import Document
from drafthorse.models.note import IncludedNote
from drafthorse.models.party import TaxRegistration
from drafthorse.models.payment import PaymentMeans, PaymentTerms
from drafthorse.models.tradelines import LineItem
from sqlalchemy.orm import Session

from app.models.app_setting import AppSetting
from app.models.invoice import Invoice

GUIDELINE_EN16931 = "urn:cen.eu:en16931:2017"
CENT = Decimal("0.01")

# Einheiten nach UN/ECE Recommendation 20 (Pflicht in EN 16931, Regel BR-CL-23)
UNIT_CODES = {
    "stk": "H87", "stück": "H87", "stueck": "H87", "st": "H87", "h87": "H87", "c62": "C62",
    "std": "HUR", "stunde": "HUR", "stunden": "HUR", "h": "HUR", "hur": "HUR",
    "min": "MIN", "minute": "MIN", "minuten": "MIN",
    "l": "LTR", "liter": "LTR", "ltr": "LTR", "ml": "MLT",
    "kg": "KGM", "g": "GRM", "m": "MTR", "cm": "CMT", "km": "KMT",
    "satz": "SET", "set": "SET", "paar": "PR", "pauschal": "LS", "psch": "LS", "ls": "LS",
}

COUNTRY_CODES = {
    "deutschland": "DE", "germany": "DE", "österreich": "AT", "oesterreich": "AT", "austria": "AT",
    "schweiz": "CH", "switzerland": "CH", "niederlande": "NL", "frankreich": "FR", "italien": "IT",
    "polen": "PL", "tschechien": "CZ", "belgien": "BE", "luxemburg": "LU", "dänemark": "DK",
}

DEFAULT_EXEMPTION_NOTE = "Positionen mit 0 % MwSt sind von der Umsatzsteuer befreit."

# Zahlungsart-Codes (UNTDID 4461)
PAYMENT_SEPA_TRANSFER = "58"
PAYMENT_NOT_DEFINED = "1"

_PLZ_CITY = re.compile(r"^(?:D-)?(\d{4,5})\s+(.+)$")


def _money(value: Decimal) -> Decimal:
    """Auf 2 Nachkommastellen kaufmännisch runden („-0,00“ wird zu „0,00“, Regel BR-E-09)."""
    result = Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)
    return result if result != 0 else Decimal("0.00")


def _unit_code(unit: str | None) -> str:
    """Freitext-Einheit in UN/ECE-Code übersetzen (Standard: Stück H87)."""
    if not unit:
        return "H87"
    return UNIT_CODES.get(unit.strip().lower().rstrip("."), "H87")


def _country_code(country: str | None) -> str:
    """Ländername in ISO-3166-Code übersetzen (Standard: DE)."""
    if not country:
        return "DE"
    c = country.strip()
    if len(c) == 2 and c.isalpha():
        return c.upper()
    return COUNTRY_CODES.get(c.lower(), "DE")


def _get_company_settings(db: Session) -> dict[str, str]:
    """Firmendaten aus den Einstellungen laden."""
    keys = (
        "company_name", "company_address", "company_vat_id", "company_email", "company_phone",
        "company_bank_iban", "company_bank_bic", "company_bank_account_holder",
        "invoice_vat_exemption_note",
    )
    rows = db.query(AppSetting).filter(AppSetting.key.in_(keys)).all()
    return {r.key: (r.value or "").strip() for r in rows}


def _split_company_address(address: str) -> tuple[str, str, str]:
    """Mehrzeilige Firmenadresse in (Straße, PLZ, Ort) zerlegen."""
    lines = [ln.strip() for ln in (address or "").splitlines() if ln.strip()]
    street, postal, city = "", "", ""
    for ln in lines:
        m = _PLZ_CITY.match(ln)
        if m and not postal:
            postal, city = m.group(1), m.group(2)
        elif not street:
            street = ln
    return street, postal, city


def _get_customer_name(inv: Invoice) -> str:
    """Anzeigename des Kunden."""
    c = inv.customer
    if c.company_name:
        return c.company_name
    parts = [c.first_name or "", c.last_name or ""]
    return " ".join(parts).strip() or (c.email or "Kunde")


def _get_customer_address(inv: Invoice) -> tuple[str, str, str, str]:
    """(Straße, PLZ, Ort, Ländercode) – Rechnungsadresse, sonst Hauptadresse, sonst erste Adresse."""
    addresses = list(inv.customer.addresses or [])
    for wanted in ("billing", "main", None):
        for addr in addresses:
            if wanted is None or addr.address_type == wanted:
                street = f"{addr.street} {addr.house_number or ''}".strip()
                return (street, addr.postal_code or "", addr.city or "", _country_code(getattr(addr, "country", None)))
    return ("", "", "", "DE")


def _tax_category(rate: Decimal) -> str:
    """Steuerkategorie: S = Normal-/ermäßigter Satz, E = steuerbefreit (0 %)."""
    return "S" if rate > 0 else "E"


def build_zugferd_xml(db: Session, inv: Invoice) -> bytes:
    """E-Rechnungs-XML nach EN 16931 (Factur-X/ZUGFeRD Profil EN16931) erzeugen."""
    settings = _get_company_settings(db)
    company_name = settings.get("company_name") or "WareVision"
    company_vat = settings.get("company_vat_id", "")
    iban = settings.get("company_bank_iban", "").replace(" ", "")
    seller_street, seller_postal, seller_city = _split_company_address(settings.get("company_address", ""))

    cust_name = _get_customer_name(inv)
    cust_street, cust_postal, cust_city, cust_country = _get_customer_address(inv)

    doc = Document()
    doc.context.guideline_parameter.id = GUIDELINE_EN16931
    doc.header.id = inv.invoice_number                      # BT-1
    doc.header.type_code = "380"                            # BT-3 Handelsrechnung
    doc.header.issue_date_time = inv.invoice_date           # BT-2

    original = getattr(inv, "cancellation_of", None)
    if original is not None:
        note = IncludedNote()
        note.content = f"Stornorechnung zu Rechnung {original.invoice_number}"
        doc.header.notes.add(note)
        doc.trade.settlement.invoice_referenced_document.issuer_assigned_id = original.invoice_number  # BT-25
        doc.trade.settlement.invoice_referenced_document.issue_date_time = original.invoice_date      # BT-26

    # Verkäufer (BG-4)
    seller = doc.trade.agreement.seller
    seller.name = company_name
    if seller_street:
        seller.address.line_one = seller_street[:100]
    if seller_postal:
        seller.address.postcode = seller_postal
    if seller_city:
        seller.address.city_name = seller_city[:100]
    seller.address.country_id = "DE"
    if company_vat:
        seller.tax_registrations.add(TaxRegistration(id=("VA", company_vat)))
    if settings.get("company_email"):
        seller.contact.email.address = settings["company_email"]
    if settings.get("company_phone"):
        seller.contact.telephone.number = settings["company_phone"]

    # Käufer (BG-7)
    buyer = doc.trade.agreement.buyer
    buyer.name = cust_name
    if cust_street:
        buyer.address.line_one = cust_street[:100]
    if cust_postal:
        buyer.address.postcode = cust_postal
    if cust_city:
        buyer.address.city_name = cust_city[:100]
    buyer.address.country_id = cust_country
    if inv.customer.vat_id:
        buyer.tax_registrations.add(TaxRegistration(id=("VA", inv.customer.vat_id)))

    # Leistungsdatum (BT-72)
    if getattr(inv, "service_date", None):
        doc.trade.delivery.event.occurrence = inv.service_date

    currency = inv.currency or "EUR"
    doc.trade.settlement.currency_code = currency          # BT-5

    # Zahlungsart (BG-16): SEPA-Überweisung nur mit IBAN (Regel BR-61)
    pm = PaymentMeans()
    if iban:
        pm.type_code = PAYMENT_SEPA_TRANSFER
        pm.payee_account.iban = iban
        if settings.get("company_bank_account_holder"):
            pm.payee_account.account_name = settings["company_bank_account_holder"]
    else:
        pm.type_code = PAYMENT_NOT_DEFINED
    doc.trade.settlement.payment_means.add(pm)

    # Zahlungsbedingungen / Fälligkeit (BT-9)
    if inv.due_date:
        terms = PaymentTerms()
        terms.description = f"Zahlbar bis {inv.due_date.strftime('%d.%m.%Y')}"
        terms.due = inv.due_date
        doc.trade.settlement.terms.add(terms)

    # Positionen (BG-25)
    basis_by_rate: dict[Decimal, Decimal] = {}
    line_total = Decimal("0.00")
    for i, item in enumerate(inv.items, 1):
        rate = Decimal(item.vat_rate).quantize(CENT)
        line_net = _money(item.line_total_net)
        li = LineItem()
        li.document.line_id = str(i)                                   # BT-126
        li.product.name = (item.description or "Position")[:500]       # BT-153
        li.agreement.net.amount = Decimal(item.unit_price)             # BT-146
        li.delivery.billed_quantity = (Decimal(item.quantity), _unit_code(item.unit))  # BT-129/130
        li.settlement.trade_tax.type_code = "VAT"
        li.settlement.trade_tax.category_code = _tax_category(rate)    # BT-151
        li.settlement.trade_tax.rate_applicable_percent = rate         # BT-152
        li.settlement.monetary_summation.total_amount = line_net       # BT-131
        doc.trade.items.add(li)
        basis_by_rate[rate] = basis_by_rate.get(rate, Decimal("0.00")) + line_net
        line_total += line_net

    # Steueraufschlüsselung (BG-23)
    tax_total = Decimal("0.00")
    for rate in sorted(basis_by_rate):
        basis = basis_by_rate[rate]
        amount = _money(basis * rate / 100)
        tt = ApplicableTradeTax()
        tt.calculated_amount = amount
        tt.type_code = "VAT"
        tt.basis_amount = basis
        tt.category_code = _tax_category(rate)
        if rate == 0:
            tt.exemption_reason = settings.get("invoice_vat_exemption_note") or DEFAULT_EXEMPTION_NOTE  # BT-120
        tt.rate_applicable_percent = rate
        doc.trade.settlement.trade_tax.add(tt)
        tax_total += amount

    # Summen (BG-22)
    grand_total = line_total + tax_total
    ms = doc.trade.settlement.monetary_summation
    ms.line_total = line_total                    # BT-106
    ms.tax_basis_total = (line_total, None)       # BT-109
    ms.tax_total = (tax_total, currency)          # BT-110
    ms.grand_total = (grand_total, None)          # BT-112
    ms.due_amount = grand_total                   # BT-115

    return doc.serialize(schema=None)


def generate_zugferd_pdf(db: Session, inv: Invoice) -> bytes:
    """Rechnungs-PDF mit eingebetteter E-Rechnung (Factur-X/ZUGFeRD EN16931) erzeugen."""
    from facturx import generate_from_binary
    from app.services.pdf import generate_invoice_pdf
    from app.services.pdfa import add_output_intent

    # PDF/A-3: Farbprofil ergänzen (Schriften werden in pdf.py eingebettet)
    pdf_bytes = add_output_intent(generate_invoice_pdf(db, inv))
    xml_bytes = build_zugferd_xml(db, inv)
    # check_xsd=True: lieber Fehler melden als eine formal ungültige E-Rechnung versenden
    return generate_from_binary(pdf_bytes, xml_bytes, flavor="factur-x", level="en16931", check_xsd=True)


def _parse_zugferd_xml(xml_str: str) -> dict:
    """ZUGFeRD/Factur-X XML in ein strukturiertes Dict übersetzen."""
    import xml.etree.ElementTree as ET

    ns = {
        "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
        "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
        "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
    }

    root = ET.fromstring(xml_str)

    def text(elem, path: str) -> str:
        if elem is None:
            return ""
        found = elem.find(path, ns)
        return (found.text or "").strip() if found is not None else ""

    def parse_date(s: str) -> str:
        s = s.strip()
        if len(s) == 8 and s.isdigit():
            return f"{s[:4]}-{s[4:6]}-{s[6:]}"
        return s

    doc_el = root.find("rsm:ExchangedDocument", ns)
    invoice_number = text(doc_el, "ram:ID")
    type_code = text(doc_el, "ram:TypeCode")
    invoice_date = parse_date(text(doc_el, "ram:IssueDateTime/udt:DateTimeString"))

    trade = root.find("rsm:SupplyChainTradeTransaction", ns)
    agreement = trade.find("ram:ApplicableHeaderTradeAgreement", ns) if trade is not None else None
    settlement = trade.find("ram:ApplicableHeaderTradeSettlement", ns) if trade is not None else None

    seller = agreement.find("ram:SellerTradeParty", ns) if agreement is not None else None
    seller_name = text(seller, "ram:Name")
    seller_vat = text(seller, "ram:SpecifiedTaxRegistration/ram:ID")
    seller_street = text(seller, "ram:PostalTradeAddress/ram:LineOne")
    seller_postal = text(seller, "ram:PostalTradeAddress/ram:PostcodeCode")
    seller_city = text(seller, "ram:PostalTradeAddress/ram:CityName")

    buyer = agreement.find("ram:BuyerTradeParty", ns) if agreement is not None else None
    buyer_name = text(buyer, "ram:Name")

    currency = text(settlement, "ram:InvoiceCurrencyCode") or "EUR"

    due_date = ""
    payment_terms = settlement.find("ram:SpecifiedTradePaymentTerms", ns) if settlement is not None else None
    if payment_terms is not None:
        due_date = parse_date(text(payment_terms, "ram:DueDateDateTime/udt:DateTimeString"))

    summation = settlement.find("ram:SpecifiedTradeSettlementHeaderMonetarySummation", ns) if settlement is not None else None
    net_amount = text(summation, "ram:TaxBasisTotalAmount")
    vat_amount = text(summation, "ram:TaxTotalAmount")
    gross_amount = text(summation, "ram:GrandTotalAmount")

    items = []
    if trade is not None:
        for line in trade.findall("ram:IncludedSupplyChainTradeLineItem", ns):
            line_doc = line.find("ram:AssociatedDocumentLineDocument", ns)
            line_id = text(line_doc, "ram:LineID")

            product = line.find("ram:SpecifiedTradeProduct", ns)
            name = text(product, "ram:Name")

            delivery = line.find("ram:SpecifiedLineTradeDelivery", ns)
            billed_qty_el = delivery.find("ram:BilledQuantity", ns) if delivery is not None else None
            quantity = (billed_qty_el.text or "1").strip() if billed_qty_el is not None else "1"
            unit = billed_qty_el.get("unitCode", "") if billed_qty_el is not None else ""

            line_agr = line.find("ram:SpecifiedLineTradeAgreement", ns)
            unit_price = text(line_agr, "ram:NetPriceProductTradePrice/ram:ChargeAmount")

            line_sett = line.find("ram:SpecifiedLineTradeSettlement", ns)
            vat_rate = text(line_sett, "ram:ApplicableTradeTax/ram:RateApplicablePercent")
            line_total = text(line_sett, "ram:SpecifiedTradeSettlementLineMonetarySummation/ram:LineTotalAmount")

            items.append({
                "line_id": line_id,
                "description": name,
                "quantity": quantity,
                "unit": unit,
                "unit_price": unit_price,
                "vat_rate": vat_rate,
                "line_total_net": line_total,
            })

    return {
        "invoice_number": invoice_number,
        "type_code": type_code,
        "invoice_date": invoice_date,
        "due_date": due_date,
        "currency": currency,
        "seller": {
            "name": seller_name,
            "vat_id": seller_vat,
            "street": seller_street,
            "postal_code": seller_postal,
            "city": seller_city,
        },
        "buyer": {"name": buyer_name},
        "net_amount": net_amount,
        "vat_amount": vat_amount,
        "gross_amount": gross_amount,
        "items": items,
    }


def parse_zugferd_pdf(pdf_bytes: bytes) -> dict:
    """ZUGFeRD/Factur-X-PDF einlesen und strukturierte Rechnungsdaten zurückgeben."""
    from facturx import get_facturx_xml_from_pdf

    result = get_facturx_xml_from_pdf(pdf_bytes, check_xsd=False)

    # factur-x gibt False zurück wenn kein eingebettetes XML gefunden wurde
    if result is False or result is None:
        raise ValueError("Diese PDF enthält kein eingebettetes ZUGFeRD-XML. Bitte nur ZUGFeRD/Factur-X kompatible PDFs importieren.")

    # factur-x kann (xml_bytes, filename)-Tuple oder dict zurückgeben
    xml_raw: bytes | str | None = None
    # factur-x liefert (Dateiname, XML-Bytes)
    if isinstance(result, tuple) and len(result) > 1:
        xml_raw = result[1]
    elif isinstance(result, dict) and result:
        xml_raw = next(iter(result.values()))
    elif isinstance(result, (bytes, str)):
        xml_raw = result

    if not xml_raw or isinstance(xml_raw, bool):
        raise ValueError("ZUGFeRD-XML konnte nicht aus der PDF extrahiert werden.")

    xml_str = xml_raw.decode("utf-8", errors="replace") if isinstance(xml_raw, bytes) else xml_raw
    return _parse_zugferd_xml(xml_str)
