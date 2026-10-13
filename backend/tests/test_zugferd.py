"""Tests: ZUGFeRD Export und Import."""

import io
import pytest


class TestZUGFeRDExport:
    def test_zugferd_pdf_export(self, admin_client, sample_invoice):
        """ZUGFeRD-PDF für eine Rechnung generieren."""
        res = admin_client.get(f"/api/v1/invoices/{sample_invoice.id}/zugferd")
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("application/pdf")
        assert res.content[:4] == b"%PDF"
        assert len(res.content) > 500

    def test_zugferd_export_dateiname(self, admin_client, sample_invoice):
        """Content-Disposition enthält Rechnungsnummer."""
        res = admin_client.get(f"/api/v1/invoices/{sample_invoice.id}/zugferd")
        assert res.status_code == 200
        assert sample_invoice.invoice_number in res.headers.get("content-disposition", "")

    def test_zugferd_export_unbekannte_rechnung(self, admin_client):
        """Unbekannte Rechnung → 404."""
        res = admin_client.get("/api/v1/invoices/00000000-0000-0000-0000-000000000000/zugferd")
        assert res.status_code == 404

    def test_zugferd_service_direkt(self, db, sample_invoice):
        """generate_zugferd_pdf gibt gültiges PDF zurück."""
        from app.services.zugferd import generate_zugferd_pdf

        pdf_bytes = generate_zugferd_pdf(db, sample_invoice)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"


class TestZUGFeRDImport:
    def _plain_pdf(self) -> bytes:
        """Minimales PDF ohne ZUGFeRD-XML."""
        return (
            b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
            b"xref\n0 1\n0000000000 65535 f\n"
            b"trailer\n<< /Size 1 /Root 1 0 R >>\nstartxref\n9\n%%EOF"
        )

    def test_import_kein_pdf_abgelehnt(self, admin_client):
        """Keine PDF-Datei → 400."""
        res = admin_client.post(
            "/api/v1/invoices/zugferd/import",
            files={"file": ("rechnung.txt", io.BytesIO(b"kein pdf"), "text/plain")},
        )
        assert res.status_code == 400

    def test_import_leere_datei_abgelehnt(self, admin_client):
        """Leere Datei → 400."""
        res = admin_client.post(
            "/api/v1/invoices/zugferd/import",
            files={"file": ("leer.pdf", io.BytesIO(b""), "application/pdf")},
        )
        assert res.status_code == 400

    def test_import_pdf_ohne_xml_schlaegt_fehl(self, admin_client):
        """PDF ohne eingebettetes ZUGFeRD-XML → 422."""
        res = admin_client.post(
            "/api/v1/invoices/zugferd/import",
            files={"file": ("normal.pdf", io.BytesIO(self._plain_pdf()), "application/pdf")},
        )
        assert res.status_code == 422

    def test_import_nur_fuer_authentifizierte(self, client):
        """Unauthentifizierter Zugriff → 401/403."""
        res = client.post(
            "/api/v1/invoices/zugferd/import",
            files={"file": ("test.pdf", io.BytesIO(self._plain_pdf()), "application/pdf")},
        )
        assert res.status_code in (401, 403)


class TestZUGFeRDXMLParser:
    MINIMAL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice
    xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
    xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
    xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
  <rsm:ExchangedDocument>
    <ram:ID>RE-2026-0042</ram:ID>
    <ram:TypeCode>380</ram:TypeCode>
    <ram:IssueDateTime>
      <udt:DateTimeString format="102">20260115</udt:DateTimeString>
    </ram:IssueDateTime>
  </rsm:ExchangedDocument>
  <rsm:SupplyChainTradeTransaction>
    <ram:ApplicableHeaderTradeAgreement>
      <ram:SellerTradeParty>
        <ram:Name>Quad Paradies Schoner</ram:Name>
      </ram:SellerTradeParty>
      <ram:BuyerTradeParty>
        <ram:Name>Max Mustermann</ram:Name>
      </ram:BuyerTradeParty>
    </ram:ApplicableHeaderTradeAgreement>
    <ram:ApplicableHeaderTradeSettlement>
      <ram:InvoiceCurrencyCode>EUR</ram:InvoiceCurrencyCode>
      <ram:SpecifiedTradeSettlementHeaderMonetarySummation>
        <ram:TaxBasisTotalAmount>100.00</ram:TaxBasisTotalAmount>
        <ram:TaxTotalAmount>19.00</ram:TaxTotalAmount>
        <ram:GrandTotalAmount>119.00</ram:GrandTotalAmount>
        <ram:DuePayableAmount>119.00</ram:DuePayableAmount>
      </ram:SpecifiedTradeSettlementHeaderMonetarySummation>
    </ram:ApplicableHeaderTradeSettlement>
    <ram:IncludedSupplyChainTradeLineItem/>
  </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>"""

    def test_xml_parser_rechnungsnummer(self):
        """Parser extrahiert Rechnungsnummer."""
        from app.services.zugferd import _parse_zugferd_xml

        result = _parse_zugferd_xml(self.MINIMAL_XML)
        assert result["invoice_number"] == "RE-2026-0042"

    def test_xml_parser_datum(self):
        """Parser konvertiert Datum von YYYYMMDD."""
        from app.services.zugferd import _parse_zugferd_xml

        result = _parse_zugferd_xml(self.MINIMAL_XML)
        assert result["invoice_date"] == "2026-01-15"

    def test_xml_parser_betraege(self):
        """Parser liest Netto, MwSt und Brutto."""
        from app.services.zugferd import _parse_zugferd_xml

        result = _parse_zugferd_xml(self.MINIMAL_XML)
        assert result["net_amount"] == "100.00"
        assert result["vat_amount"] == "19.00"
        assert result["gross_amount"] == "119.00"

    def test_xml_parser_kaeufer(self):
        """Parser liest Käufername."""
        from app.services.zugferd import _parse_zugferd_xml

        result = _parse_zugferd_xml(self.MINIMAL_XML)
        assert result["buyer"]["name"] == "Max Mustermann"

    def test_xml_parser_ungueltig(self):
        """Ungültiges XML wirft Exception."""
        from app.services.zugferd import _parse_zugferd_xml

        with pytest.raises(Exception):
            _parse_zugferd_xml("das ist kein xml <<<")
