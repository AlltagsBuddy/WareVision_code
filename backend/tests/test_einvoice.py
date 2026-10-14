"""Tests: E-Rechnung – Ausgang (ZUGFeRD EN16931, PDF/A-3) und Eingang (ZUGFeRD/XRechnung, GoBD-Archiv)."""

import os
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest

INC = "/api/v1/incoming-invoices"

UBL = b"""<?xml version="1.0" encoding="UTF-8"?>
<ubl:Invoice xmlns:ubl="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
 xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
<cbc:CustomizationID>urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0</cbc:CustomizationID>
<cbc:ID>UBL-4711</cbc:ID><cbc:IssueDate>2026-10-01</cbc:IssueDate><cbc:DueDate>2026-10-15</cbc:DueDate>
<cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode><cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>
<cac:AccountingSupplierParty><cac:Party><cac:PostalAddress><cbc:StreetName>Hauptstr 1</cbc:StreetName>
<cbc:CityName>Berlin</cbc:CityName><cbc:PostalZone>10115</cbc:PostalZone></cac:PostalAddress>
<cac:PartyTaxScheme><cbc:CompanyID>DE999999999</cbc:CompanyID></cac:PartyTaxScheme>
<cac:PartyLegalEntity><cbc:RegistrationName>Moto Teile AG</cbc:RegistrationName></cac:PartyLegalEntity></cac:Party></cac:AccountingSupplierParty>
<cac:Delivery><cbc:ActualDeliveryDate>2026-09-30</cbc:ActualDeliveryDate></cac:Delivery>
<cac:TaxTotal><cbc:TaxAmount currencyID="EUR">26.60</cbc:TaxAmount></cac:TaxTotal>
<cac:LegalMonetaryTotal><cbc:TaxExclusiveAmount currencyID="EUR">140.00</cbc:TaxExclusiveAmount>
<cbc:TaxInclusiveAmount currencyID="EUR">166.60</cbc:TaxInclusiveAmount></cac:LegalMonetaryTotal>
<cac:InvoiceLine><cbc:ID>1</cbc:ID><cbc:InvoicedQuantity unitCode="H87">2</cbc:InvoicedQuantity>
<cbc:LineExtensionAmount currencyID="EUR">140.00</cbc:LineExtensionAmount><cac:Item><cbc:Name>Bremsbelag</cbc:Name>
<cac:ClassifiedTaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>19</cbc:Percent></cac:ClassifiedTaxCategory></cac:Item>
<cac:Price><cbc:PriceAmount currencyID="EUR">70.00</cbc:PriceAmount></cac:Price></cac:InvoiceLine>
</ubl:Invoice>"""

UBL_CREDIT = UBL.replace(b"ubl:Invoice", b"ubl:CreditNote").replace(
    b"urn:oasis:names:specification:ubl:schema:xsd:Invoice-2", b"urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
).replace(b"InvoiceTypeCode", b"CreditNoteTypeCode").replace(b">380<", b">381<").replace(
    b"InvoiceLine", b"CreditNoteLine").replace(b"InvoicedQuantity", b"CreditedQuantity").replace(b"UBL-4711", b"GS-1")


def _create_invoice(client, customer_id, items, service_date="2026-10-10"):
    res = client.post("/api/v1/invoices", json={
        "customer_id": str(customer_id), "invoice_date": "2026-10-13", "service_date": service_date, "items": items,
    })
    assert res.status_code == 201, res.text
    return res.json()


MIXED = [
    {"description": "Arbeit", "quantity": 1.5, "unit": "Std.", "unit_price": 89, "vat_rate": 19},
    {"description": "Fachbuch", "quantity": 1, "unit": "Stk", "unit_price": 24.99, "vat_rate": 7},
    {"description": "TÜV-Gebühr", "quantity": 1, "unit": "Stk", "unit_price": 98.5, "vat_rate": 0},
]


def _xml_from_pdf(pdf: bytes) -> bytes:
    from facturx import get_facturx_xml_from_pdf
    _, xml = get_facturx_xml_from_pdf(BytesIO(pdf), check_xsd=False)
    return xml


def _assert_en16931_xsd(xml: bytes) -> None:
    """XML gegen das offizielle Factur-X-Schema (Profil EN16931) prüfen."""
    from facturx import xml_check_xsd
    assert xml_check_xsd(xml, flavor="factur-x", level="en16931") is True


class TestRechnungSteuer:
    def test_mwst_je_steuersatz(self, admin_client, b2b_customer):
        inv = _create_invoice(admin_client, b2b_customer.id, MIXED)
        # 19 %: 133,50 → 25,365 → 25,37 ; 7 %: 24,99 → 1,7493 → 1,75 ; 0 %: 0
        assert inv["net_amount"] == "256.99"
        assert inv["vat_amount"] == "27.12"
        assert inv["gross_amount"] == "284.11"

    def test_leistungsdatum(self, admin_client, b2b_customer):
        inv = _create_invoice(admin_client, b2b_customer.id, MIXED[:1])
        assert inv["service_date"] == "2026-10-10"

    def test_leistungsdatum_standard_rechnungsdatum(self, admin_client, b2b_customer):
        inv = _create_invoice(admin_client, b2b_customer.id, MIXED[:1], service_date=None)
        assert inv["service_date"] == inv["invoice_date"]

    def test_pdf_pflichtangaben(self, admin_client, b2b_customer, company_settings, db):
        from pypdf import PdfReader
        from app.models.app_setting import AppSetting

        db.add(AppSetting(key="invoice_vat_exemption_note", value="TÜV-Gebühr: durchlaufender Posten"))
        db.flush()
        inv = _create_invoice(admin_client, b2b_customer.id, MIXED)
        text = PdfReader(BytesIO(admin_client.get(f"/api/v1/invoices/{inv['id']}/pdf").content)).pages[0].extract_text()
        assert "Leistungsdatum: 10.10.2026" in text
        assert "MwSt 19 % auf 133,50 €" in text and "MwSt 7 % auf 24,99 €" in text
        assert "284,11 €" in text                       # deutsches Zahlenformat
        assert "Industriestraße 5" in text               # vollständige Kundenadresse
        assert "TÜV-Gebühr: durchlaufender Posten" in text  # Hinweis Steuerbefreiung

    def test_lange_beschreibung_nicht_abgeschnitten(self, admin_client, b2b_customer):
        from pypdf import PdfReader

        long = "Inspektion nach Herstellervorgabe inklusive Prüfung aller Bremsleitungen und Probefahrt Ende"
        inv = _create_invoice(admin_client, b2b_customer.id, [{"description": long, "quantity": 1, "unit_price": 10, "vat_rate": 19}])
        text = PdfReader(BytesIO(admin_client.get(f"/api/v1/invoices/{inv['id']}/pdf").content)).pages[0].extract_text()
        assert "Probefahrt Ende" in text.replace("\n", " ")


class TestZugferdAusgang:
    def test_en16931_gueltig_mit_allen_angaben(self, admin_client, b2b_customer, company_settings):
        inv = _create_invoice(admin_client, b2b_customer.id, MIXED)
        res = admin_client.get(f"/api/v1/invoices/{inv['id']}/zugferd")
        assert res.status_code == 200, res.text
        xml = _xml_from_pdf(res.content)
        _assert_en16931_xsd(xml)
        assert b"urn:cen.eu:en16931:2017" in xml
        assert b"20261010" in xml                     # Leistungsdatum (BT-72)
        assert b"DE02120300000000202051" in xml       # IBAN
        assert b"<ram:CityName>Bamberg</ram:CityName>" in xml
        assert b"HUR" in xml                           # Einheit Stunde
        assert b"<ram:CategoryCode>E</ram:CategoryCode>" in xml  # 0 % = befreit

    def test_storno_gueltig(self, admin_client, b2b_customer, company_settings):
        inv = _create_invoice(admin_client, b2b_customer.id, MIXED)
        admin_client.post(f"/api/v1/invoices/{inv['id']}/issue")
        assert admin_client.post(f"/api/v1/invoices/{inv['id']}/cancel", json={"reason": "Test"}).status_code == 200
        storno = next(i for i in admin_client.get("/api/v1/invoices").json() if i["invoice_number"].startswith("STO-"))
        assert storno["service_date"] == "2026-10-10"
        xml = _xml_from_pdf(admin_client.get(f"/api/v1/invoices/{storno['id']}/zugferd").content)
        _assert_en16931_xsd(xml)
        assert b"-0.00" not in xml                     # Regel BR-E-09
        assert inv["invoice_number"].encode() in xml   # Verweis auf Originalrechnung (BT-25)

    def test_pdfa_bausteine(self, admin_client, b2b_customer, company_settings):
        from pypdf import PdfReader

        inv = _create_invoice(admin_client, b2b_customer.id, MIXED[:1])
        reader = PdfReader(BytesIO(admin_client.get(f"/api/v1/invoices/{inv['id']}/zugferd").content))
        root = reader.trailer["/Root"]
        intents = root["/OutputIntents"]
        assert intents[0].get_object()["/S"] == "/GTS_PDFA1"
        assert b"pdfaid:part>3" in root["/Metadata"].get_object().get_data()
        assert "factur-x.xml" in reader.attachments

    def test_schriften_eingebettet(self, admin_client, b2b_customer):
        """Nur wenn Liberation Sans installiert ist (im Docker-Image vorhanden)."""
        from pypdf import PdfReader
        from app.services.pdfa import register_embedded_fonts

        if not register_embedded_fonts():
            pytest.skip("Liberation-Schriften nicht installiert")
        inv = _create_invoice(admin_client, b2b_customer.id, MIXED[:1])
        reader = PdfReader(BytesIO(admin_client.get(f"/api/v1/invoices/{inv['id']}/pdf").content))
        fonts = reader.pages[0]["/Resources"]["/Font"]
        for ref in fonts.values():
            font = ref.get_object()
            desc = font.get("/FontDescriptor")
            assert desc is not None and "/FontFile2" in desc.get_object(), f"Schrift nicht eingebettet: {font['/BaseFont']}"

    def test_schematron_en16931(self, admin_client, b2b_customer, company_settings):
        """Volle Regelprüfung (EN16931-Schematron) – optional, wenn saxonche + XSLT vorhanden.

        XSLT: github.com/ConnectingEurope/eInvoicing-EN16931 → cii/xslt/EN16931-CII-validation.xslt
        Pfad per Umgebungsvariable EN16931_CII_XSLT angeben.
        """
        xslt = os.getenv("EN16931_CII_XSLT")
        saxon = pytest.importorskip("saxonche")
        if not xslt or not os.path.isfile(xslt):
            pytest.skip("EN16931_CII_XSLT nicht gesetzt")
        from lxml import etree

        for items in (MIXED, MIXED[:1]):
            inv = _create_invoice(admin_client, b2b_customer.id, items)
            xml = _xml_from_pdf(admin_client.get(f"/api/v1/invoices/{inv['id']}/zugferd").content)
            with saxon.PySaxonProcessor(license=False) as proc:
                exe = proc.new_xslt30_processor().compile_stylesheet(stylesheet_file=xslt)
                out = exe.transform_to_string(xdm_node=proc.parse_xml(xml_text=xml.decode()))
            ns = {"svrl": "http://purl.oclc.org/dsdl/svrl"}
            failed = etree.fromstring(out.encode()).findall(".//svrl:failed-assert", ns)
            assert not failed, [f.get("id") for f in failed]


class TestEingangManuell:
    def test_crud(self, admin_client):
        res = admin_client.post(INC, json={"supplier_name": "Öl GmbH", "invoice_number": "R-1", "invoice_date": "2026-10-01",
                                           "net_amount": 100, "vat_rate": 19, "category": "Ersatzteile"})
        assert res.status_code == 201, res.text
        inv = res.json()
        assert (inv["vat_amount"], inv["gross_amount"]) == ("19.00", "119.00")
        res = admin_client.patch(f"{INC}/{inv['id']}", json={"net_amount": 200})
        assert res.json()["gross_amount"] == "238.00"
        assert admin_client.patch(f"{INC}/{inv['id']}", json={"status": "paid"}).json()["status"] == "paid"
        assert admin_client.delete(f"{INC}/{inv['id']}").status_code == 204

    def test_pdf_anhang(self, admin_client):
        inv = admin_client.post(INC, json={"supplier_name": "X", "invoice_number": "R-2", "invoice_date": "2026-10-01",
                                           "net_amount": 10}).json()
        pdf = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
        res = admin_client.post(f"{INC}/{inv['id']}/upload-pdf", files={"file": ("r.pdf", pdf, "application/pdf")})
        assert res.status_code == 200
        assert admin_client.get(f"{INC}/{inv['id']}/pdf").content == pdf

    def test_nur_admin_anlegen(self, werkstatt_client):
        res = werkstatt_client.post(INC, json={"supplier_name": "X", "invoice_number": "1", "invoice_date": "2026-10-01", "net_amount": 1})
        assert res.status_code == 403


class TestEingangEInvoice:
    def _import(self, client, content, name, ctype):
        return client.post(f"{INC}/import-einvoice", files={"file": (name, content, ctype)})

    def test_xrechnung_ubl(self, admin_client):
        res = self._import(admin_client, UBL, "r.xml", "application/xml")
        assert res.status_code == 201, res.text
        inv = res.json()
        assert inv["einvoice_format"] == "xrechnung_ubl"
        assert (inv["supplier_name"], inv["invoice_number"]) == ("Moto Teile AG", "UBL-4711")
        assert (inv["net_amount"], inv["vat_amount"], inv["gross_amount"]) == ("140.00", "26.60", "166.60")
        assert (inv["service_date"], inv["due_date"], inv["supplier_vat_id"]) == ("2026-09-30", "2026-10-15", "DE999999999")
        assert len(inv["original_sha256"]) == 64
        # Original unverändert abrufbar
        assert admin_client.get(f"{INC}/{inv['id']}/original").content == UBL

    def test_gutschrift_markiert(self, admin_client):
        inv = self._import(admin_client, UBL_CREDIT, "g.xml", "application/xml").json()
        assert "Gutschrift" in inv["notes"]

    def test_eigene_zugferd_rechnung_roundtrip(self, admin_client, b2b_customer, company_settings):
        out = _create_invoice(admin_client, b2b_customer.id, MIXED)
        pdf = admin_client.get(f"/api/v1/invoices/{out['id']}/zugferd").content
        res = self._import(admin_client, pdf, "z.pdf", "application/pdf")
        assert res.status_code == 201, res.text
        inv = res.json()
        assert inv["einvoice_format"] == "zugferd"
        assert inv["gross_amount"] == out["gross_amount"]
        assert inv["service_date"] == "2026-10-10"
        assert "Mehrere MwSt-Sätze" in inv["notes"]
        assert admin_client.get(f"{INC}/{inv['id']}/pdf").content == pdf

    def test_xrechnung_cii(self, admin_client, b2b_customer, company_settings):
        out = _create_invoice(admin_client, b2b_customer.id, MIXED[:1])
        xml = _xml_from_pdf(admin_client.get(f"/api/v1/invoices/{out['id']}/zugferd").content)
        inv = self._import(admin_client, xml, "c.xml", "application/xml").json()
        assert inv["einvoice_format"] == "xrechnung_cii"

    def test_doppelimport_abgelehnt(self, admin_client):
        assert self._import(admin_client, UBL, "r.xml", "application/xml").status_code == 201
        res = self._import(admin_client, UBL, "r2.xml", "application/xml")
        assert res.status_code == 409

    def test_schutz_gobd(self, admin_client):
        inv = self._import(admin_client, UBL, "r.xml", "application/xml").json()
        assert admin_client.delete(f"{INC}/{inv['id']}").status_code == 400
        assert admin_client.patch(f"{INC}/{inv['id']}", json={"net_amount": 1}).status_code == 400
        assert admin_client.patch(f"{INC}/{inv['id']}", json={"status": "paid", "category": "Teile"}).status_code == 200

    def test_normale_pdf_ist_keine_erechnung(self, admin_client):
        from reportlab.pdfgen import canvas

        buf = BytesIO()
        c = canvas.Canvas(buf)
        c.drawString(100, 750, "Rechnung als normales PDF")
        c.save()
        res = self._import(admin_client, buf.getvalue(), "normal.pdf", "application/pdf")
        assert res.status_code == 422
        assert "kein eingebettetes ZUGFeRD-XML" in res.json()["detail"]

    @pytest.mark.parametrize("content,expected", [
        (b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF", "beschädigt"),
        (b"<x/>", "Unbekanntes XML-Format"),
        (b"kein xml", "keine gültige XML"),
        (b'<!DOCTYPE l [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;">]><x>&b;</x>', "keine gültige XML"),  # XML-Angriff
    ])
    def test_ungueltige_dateien(self, admin_client, content, expected):
        res = self._import(admin_client, content, "f.bin", "application/octet-stream")
        assert res.status_code == 422
        assert expected in res.json()["detail"]

    def test_fremdwaehrung_abgelehnt(self, admin_client):
        usd = UBL.replace(b">EUR<", b">USD<").replace(b'currencyID="EUR"', b'currencyID="USD"')
        res = self._import(admin_client, usd, "u.xml", "application/xml")
        assert res.status_code == 422

    def test_alter_vorschau_import(self, admin_client, b2b_customer, company_settings):
        """Vorschau-Import auf der Rechnungsseite liest das XML (früher fehlerhaft)."""
        out = _create_invoice(admin_client, b2b_customer.id, MIXED[:1])
        pdf = admin_client.get(f"/api/v1/invoices/{out['id']}/zugferd").content
        res = admin_client.post("/api/v1/invoices/zugferd/import", files={"file": ("z.pdf", pdf, "application/pdf")})
        assert res.status_code == 200
        assert res.json()["invoice_number"] == out["invoice_number"]
