"""E-Rechnungs-Import (Eingang): ZUGFeRD/Factur-X-PDF sowie XRechnung (UBL und CII).

Seit 01.01.2025 müssen Unternehmen in Deutschland E-Rechnungen empfangen können
(§ 14 UStG). Diese Datei erkennt das Format, liest die Rechnungsdaten aus und
liefert sie als Dict. Das Original wird vom Aufrufer unverändert archiviert (GoBD).
"""

from collections import Counter
from decimal import Decimal, InvalidOperation

from defusedxml import ElementTree as ET

from app.services.zugferd import _parse_zugferd_xml

NS_CII = "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
NS_UBL_INVOICE = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
NS_UBL_CREDIT = "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
NS_CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
NS_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"

FORMAT_ZUGFERD = "zugferd"
FORMAT_XRECHNUNG_CII = "xrechnung_cii"
FORMAT_XRECHNUNG_UBL = "xrechnung_ubl"

# Rechnungsart-Codes (UNTDID 1001), die eine Gutschrift bedeuten
CREDIT_NOTE_TYPE_CODES = {"381", "396", "532"}


class EInvoiceError(ValueError):
    """Fehler beim Lesen einer E-Rechnung (Meldung ist für den Nutzer gedacht)."""


def _to_decimal(value: str | None) -> Decimal | None:
    """Zahl aus XML-Text in Decimal umwandeln (leer = None)."""
    if value is None or str(value).strip() == "":
        return None
    try:
        return Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise EInvoiceError(f"Ungültiger Betrag in der E-Rechnung: {value}") from exc


def _cii_service_date(xml_str: str) -> str:
    """Leistungsdatum (BT-72) aus CII-XML lesen."""
    ns = {
        "rsm": NS_CII,
        "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
        "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
    }
    root = ET.fromstring(xml_str)
    el = root.find(
        "rsm:SupplyChainTradeTransaction/ram:ApplicableHeaderTradeDelivery/"
        "ram:ActualDeliverySupplyChainEvent/ram:OccurrenceDateTime/udt:DateTimeString",
        ns,
    )
    s = (el.text or "").strip() if el is not None else ""
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return s


def _parse_cii(xml_str: str) -> dict:
    """CII-XML (ZUGFeRD / XRechnung-CII) lesen."""
    data = _parse_zugferd_xml(xml_str)
    data["service_date"] = _cii_service_date(xml_str)
    return data


def _parse_ubl(root) -> dict:
    """XRechnung im UBL-Format (Invoice oder CreditNote) lesen."""
    is_credit = root.tag == f"{{{NS_UBL_CREDIT}}}CreditNote"
    ns = {"cac": NS_CAC, "cbc": NS_CBC}

    def text(elem, path: str) -> str:
        if elem is None:
            return ""
        found = elem.find(path, ns)
        return (found.text or "").strip() if found is not None else ""

    type_code = text(root, "cbc:CreditNoteTypeCode" if is_credit else "cbc:InvoiceTypeCode")
    if is_credit and not type_code:
        type_code = "381"

    due_date = text(root, "cbc:DueDate") or text(root, "cac:PaymentMeans/cbc:PaymentDueDate")

    supplier = root.find("cac:AccountingSupplierParty/cac:Party", ns)
    seller_name = text(supplier, "cac:PartyLegalEntity/cbc:RegistrationName") or text(
        supplier, "cac:PartyName/cbc:Name"
    )

    totals = root.find("cac:LegalMonetaryTotal", ns)
    # Steuerbetrag: erstes TaxTotal mit TaxAmount in Rechnungswährung
    currency = text(root, "cbc:DocumentCurrencyCode") or "EUR"
    vat_amount = ""
    for tt in root.findall("cac:TaxTotal", ns):
        ta = tt.find("cbc:TaxAmount", ns)
        if ta is not None and ta.get("currencyID", currency) == currency:
            vat_amount = (ta.text or "").strip()
            break

    line_tag = "cac:CreditNoteLine" if is_credit else "cac:InvoiceLine"
    qty_tag = "cbc:CreditedQuantity" if is_credit else "cbc:InvoicedQuantity"
    items = []
    for line in root.findall(line_tag, ns):
        qty_el = line.find(qty_tag, ns)
        items.append({
            "line_id": text(line, "cbc:ID"),
            "description": text(line, "cac:Item/cbc:Name"),
            "quantity": (qty_el.text or "1").strip() if qty_el is not None else "1",
            "unit": qty_el.get("unitCode", "") if qty_el is not None else "",
            "unit_price": text(line, "cac:Price/cbc:PriceAmount"),
            "vat_rate": text(line, "cac:Item/cac:ClassifiedTaxCategory/cbc:Percent"),
            "line_total_net": text(line, "cbc:LineExtensionAmount"),
        })

    return {
        "invoice_number": text(root, "cbc:ID"),
        "type_code": type_code,
        "invoice_date": text(root, "cbc:IssueDate"),
        "due_date": due_date,
        "service_date": text(root, "cac:Delivery/cbc:ActualDeliveryDate"),
        "currency": currency,
        "seller": {
            "name": seller_name,
            "vat_id": text(supplier, "cac:PartyTaxScheme/cbc:CompanyID"),
            "street": text(supplier, "cac:PostalAddress/cbc:StreetName"),
            "postal_code": text(supplier, "cac:PostalAddress/cbc:PostalZone"),
            "city": text(supplier, "cac:PostalAddress/cbc:CityName"),
        },
        "buyer": {"name": text(root, "cac:AccountingCustomerParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName")},
        "net_amount": text(totals, "cbc:TaxExclusiveAmount"),
        "vat_amount": vat_amount,
        "gross_amount": text(totals, "cbc:TaxInclusiveAmount"),
        "items": items,
    }


def _parse_xml_bytes(xml_bytes: bytes) -> tuple[str, dict]:
    """XML-Datei erkennen (CII oder UBL) und auslesen. Gibt (Format, Daten) zurück."""
    try:
        root = ET.fromstring(xml_bytes)
    except Exception as exc:  # defusedxml wirft verschiedene Fehlertypen
        raise EInvoiceError("Die Datei ist keine gültige XML-Datei.") from exc

    if root.tag == f"{{{NS_CII}}}CrossIndustryInvoice":
        xml_str = xml_bytes.decode("utf-8", errors="replace")
        return FORMAT_XRECHNUNG_CII, _parse_cii(xml_str)
    if root.tag in (f"{{{NS_UBL_INVOICE}}}Invoice", f"{{{NS_UBL_CREDIT}}}CreditNote"):
        return FORMAT_XRECHNUNG_UBL, _parse_ubl(root)
    raise EInvoiceError(
        "Unbekanntes XML-Format. Unterstützt werden XRechnung (UBL oder CII) und ZUGFeRD."
    )


def _extract_xml_from_pdf(pdf_bytes: bytes) -> bytes:
    """Eingebettetes ZUGFeRD/Factur-X-XML aus einer PDF holen."""
    from facturx import get_facturx_xml_from_pdf

    # check_xsd=False: auch formal fehlerhafte Lieferanten-XMLs lesen (Inhalt wird danach geprüft)
    try:
        result = get_facturx_xml_from_pdf(pdf_bytes, check_xsd=False)
    except Exception as exc:  # beschädigte oder verschlüsselte PDF
        raise EInvoiceError("Die PDF-Datei ist beschädigt oder kann nicht gelesen werden.") from exc
    xml_raw = None
    # factur-x liefert (Dateiname, XML-Bytes)
    if isinstance(result, tuple) and len(result) > 1:
        xml_raw = result[1]
    elif isinstance(result, dict) and result:
        xml_raw = next(iter(result.values()))
    elif isinstance(result, (bytes, str)):
        xml_raw = result
    if not xml_raw or isinstance(xml_raw, bool):
        raise EInvoiceError(
            "Diese PDF enthält kein eingebettetes ZUGFeRD-XML. Eine normale PDF ist keine E-Rechnung "
            "– bitte über „+ Neue Eingangsrechnung“ manuell erfassen."
        )
    return xml_raw.encode("utf-8") if isinstance(xml_raw, str) else xml_raw


def _main_vat_rate(items: list[dict]) -> tuple[Decimal, bool]:
    """Häufigsten MwSt-Satz der Positionen ermitteln. Gibt (Satz, gemischt?) zurück."""
    rates = [_to_decimal(i.get("vat_rate")) for i in items]
    rates = [r for r in rates if r is not None]
    if not rates:
        return Decimal("19.00"), False
    counter = Counter(rates)
    return counter.most_common(1)[0][0], len(counter) > 1


def parse_einvoice(content: bytes) -> dict:
    """E-Rechnung (PDF oder XML) erkennen, lesen und prüfen.

    Rückgabe: Dict mit format, invoice_number, invoice_date, due_date, service_date,
    supplier_name, supplier_vat_id, net/vat/gross_amount (Decimal), vat_rate,
    mixed_vat_rates, is_credit_note, currency, items.
    """
    if content[:5] == b"%PDF-":
        fmt = FORMAT_ZUGFERD
        _, data = _parse_xml_bytes(_extract_xml_from_pdf(content))
    else:
        fmt, data = _parse_xml_bytes(content)

    supplier_name = (data.get("seller") or {}).get("name", "").strip()
    gross = _to_decimal(data.get("gross_amount"))
    net = _to_decimal(data.get("net_amount"))
    vat = _to_decimal(data.get("vat_amount"))

    missing = []
    if not data.get("invoice_number"):
        missing.append("Rechnungsnummer")
    if not data.get("invoice_date"):
        missing.append("Rechnungsdatum")
    if not supplier_name:
        missing.append("Lieferant")
    if gross is None:
        missing.append("Bruttobetrag")
    if missing:
        raise EInvoiceError("In der E-Rechnung fehlen Pflichtangaben: " + ", ".join(missing))

    if net is None and vat is not None:
        net = gross - vat
    if vat is None and net is not None:
        vat = gross - net
    if net is None:
        net, vat = gross, Decimal("0")

    vat_rate, mixed = _main_vat_rate(data.get("items") or [])

    return {
        "format": fmt,
        "invoice_number": data["invoice_number"].strip(),
        "invoice_date": data["invoice_date"],
        "due_date": data.get("due_date") or None,
        "service_date": data.get("service_date") or None,
        "supplier_name": supplier_name,
        "supplier_vat_id": (data.get("seller") or {}).get("vat_id") or None,
        "currency": data.get("currency") or "EUR",
        "net_amount": net,
        "vat_amount": vat,
        "gross_amount": gross,
        "vat_rate": vat_rate,
        "mixed_vat_rates": mixed,
        "is_credit_note": (data.get("type_code") or "") in CREDIT_NOTE_TYPE_CODES,
        "items": data.get("items") or [],
    }
