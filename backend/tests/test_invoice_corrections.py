"""Tests: Rechnungskorrektur (Gutschrift des Verkäufers) für ausgestellte und bezahlte Rechnungen."""

import os
from decimal import Decimal
from io import BytesIO

import pytest

V1 = "/api/v1/invoices"

ITEMS = [
    {"description": "Arbeit", "quantity": 2, "unit": "Std.", "unit_price": 89, "vat_rate": 19},
    {"description": "Fachbuch", "quantity": 1, "unit": "Stk", "unit_price": 24.99, "vat_rate": 7},
]


def _invoice(client, customer, items=ITEMS, issue=True, paid=False):
    res = client.post(V1, json={"customer_id": str(customer.id), "invoice_date": "2026-10-13",
                                "service_date": "2026-10-10", "items": items})
    assert res.status_code == 201, res.text
    inv = res.json()
    if issue:
        assert client.post(f"{V1}/{inv['id']}/issue").status_code == 200
    if paid:
        assert client.post(f"{V1}/{inv['id']}/mark-paid").status_code == 200
    return client.get(f"{V1}/{inv['id']}").json()


def _items(client, inv):
    return client.get(f"{V1}/{inv['id']}/items").json()


def _xml_from_pdf(pdf: bytes) -> bytes:
    from facturx import get_facturx_xml_from_pdf
    _, xml = get_facturx_xml_from_pdf(BytesIO(pdf), check_xsd=False)
    return xml


class TestRechnungskorrektur:
    def test_teilgutschrift_einer_position(self, admin_client, b2b_customer):
        inv = _invoice(admin_client, b2b_customer, paid=True)
        arbeit = next(i for i in _items(admin_client, inv) if i["description"] == "Arbeit")
        res = admin_client.post(f"{V1}/{inv['id']}/correction", json={
            "reason": "Eine Stunde zu viel berechnet", "lines": [{"item_id": arbeit["id"], "quantity": 1}],
        })
        assert res.status_code == 201, res.text
        rk = res.json()
        assert rk["invoice_number"].startswith("RK-") and rk["invoice_number"].endswith("-0001")
        assert rk["document_type"] == "correction"
        assert rk["corrects_invoice_id"] == inv["id"]
        assert rk["status"] == "issued"
        assert rk["service_date"] == "2026-10-10"
        assert Decimal(rk["net_amount"]) == Decimal("-89.00")
        assert Decimal(rk["vat_amount"]) == Decimal("-16.91")
        assert Decimal(rk["gross_amount"]) == Decimal("-105.91")
        assert "Eine Stunde zu viel" in rk["notes"]
        # Originalrechnung bleibt unverändert (GoBD)
        orig = admin_client.get(f"{V1}/{inv['id']}").json()
        assert orig["status"] == "paid" and orig["gross_amount"] == inv["gross_amount"]

    def test_info_zeigt_restmengen(self, admin_client, b2b_customer):
        inv = _invoice(admin_client, b2b_customer)
        arbeit = next(i for i in _items(admin_client, inv) if i["description"] == "Arbeit")
        admin_client.post(f"{V1}/{inv['id']}/correction", json={"reason": "Test", "lines": [{"item_id": arbeit["id"], "quantity": 0.5}]})
        info = admin_client.get(f"{V1}/{inv['id']}/correction-info").json()
        line = next(i for i in info["items"] if i["item_id"] == arbeit["id"])
        assert Decimal(line["credited_quantity"]) == Decimal("0.5")
        assert Decimal(line["remaining_quantity"]) == Decimal("1.5")
        assert len(info["corrections"]) == 1
        assert Decimal(info["remaining_gross"]) == Decimal(inv["gross_amount"]) - Decimal("52.96")
        assert info["vat_rates"] == ["19.00", "7.00"]

    def test_mehr_als_berechnet_abgelehnt(self, admin_client, b2b_customer):
        inv = _invoice(admin_client, b2b_customer)
        arbeit = next(i for i in _items(admin_client, inv) if i["description"] == "Arbeit")
        ok = admin_client.post(f"{V1}/{inv['id']}/correction", json={"reason": "Test", "lines": [{"item_id": arbeit["id"], "quantity": 1.5}]})
        assert ok.status_code == 201
        res = admin_client.post(f"{V1}/{inv['id']}/correction", json={"reason": "Test", "lines": [{"item_id": arbeit["id"], "quantity": 1}]})
        assert res.status_code == 400 and "höchstens 0.5" in res.json()["detail"]

    def test_preisnachlass_mit_steuersatz_der_rechnung(self, admin_client, b2b_customer):
        inv = _invoice(admin_client, b2b_customer, paid=True)
        res = admin_client.post(f"{V1}/{inv['id']}/correction", json={
            "reason": "Kulanz", "free_lines": [{"description": "Kulanznachlass", "net_amount": "10.00", "vat_rate": 19}],
        })
        assert res.status_code == 201, res.text
        assert Decimal(res.json()["gross_amount"]) == Decimal("-11.90")
        bad = admin_client.post(f"{V1}/{inv['id']}/correction", json={
            "reason": "Kulanz", "free_lines": [{"description": "Nachlass", "net_amount": "5", "vat_rate": 16}],
        })
        assert bad.status_code == 400 and "Steuersatz" in bad.json()["detail"]

    def test_nachlass_hoeher_als_rechnung_abgelehnt(self, admin_client, b2b_customer):
        inv = _invoice(admin_client, b2b_customer)
        res = admin_client.post(f"{V1}/{inv['id']}/correction", json={
            "reason": "Zu viel", "free_lines": [{"description": "Nachlass", "net_amount": "500.00", "vat_rate": 19}],
        })
        assert res.status_code == 400 and "höher als der Rechnungsbetrag" in res.json()["detail"]
        # kein halber Beleg gespeichert
        assert not [i for i in admin_client.get(V1).json() if i["invoice_number"].startswith("RK-")]

    @pytest.mark.parametrize("body", [
        {"reason": "Test"},                                   # nichts gutgeschrieben
        {"reason": "  ", "free_lines": [{"description": "x", "net_amount": "1", "vat_rate": 19}]},  # kein Grund
    ])
    def test_ungueltige_eingaben(self, admin_client, b2b_customer, body):
        inv = _invoice(admin_client, b2b_customer)
        assert admin_client.post(f"{V1}/{inv['id']}/correction", json=body).status_code in (400, 422)

    def test_entwurf_und_storno_nicht_korrigierbar(self, admin_client, b2b_customer):
        draft = _invoice(admin_client, b2b_customer, issue=False)
        free = {"reason": "Test", "free_lines": [{"description": "x", "net_amount": "1", "vat_rate": 19}]}
        assert admin_client.post(f"{V1}/{draft['id']}/correction", json=free).status_code == 400
        inv = _invoice(admin_client, b2b_customer)
        admin_client.post(f"{V1}/{inv['id']}/cancel", json={"reason": "Test"})
        assert admin_client.post(f"{V1}/{inv['id']}/correction", json=free).status_code == 400
        storno = next(i for i in admin_client.get(V1).json() if i["invoice_number"].startswith("STO-"))
        assert storno["document_type"] == "cancellation"
        assert admin_client.post(f"{V1}/{storno['id']}/correction", json=free).status_code == 400

    def test_nur_admin(self, client, werkstatt_user, admin_client, b2b_customer):
        from app.core.security import create_access_token

        inv = _invoice(admin_client, b2b_customer)
        client.headers["Authorization"] = f"Bearer {create_access_token(str(werkstatt_user.id))}"
        res = client.post(f"{V1}/{inv['id']}/correction", json={
            "reason": "Test", "free_lines": [{"description": "x", "net_amount": "1", "vat_rate": 19}]})
        assert res.status_code == 403

    def test_audit(self, admin_client, db, b2b_customer):
        from app.models.audit_log import AuditLog

        inv = _invoice(admin_client, b2b_customer)
        admin_client.post(f"{V1}/{inv['id']}/correction", json={
            "reason": "Kulanz", "free_lines": [{"description": "x", "net_amount": "1", "vat_rate": 19}]})
        log = db.query(AuditLog).filter(AuditLog.entity_type == "invoice", AuditLog.action == "correction").one()
        assert log.new_values["reason"] == "Kulanz"


class TestLagerUndStorno:
    def test_ruecknahme_ins_lager(self, admin_client, db, b2b_customer, sample_article):
        inv = _invoice(admin_client, b2b_customer, items=[
            {"article_id": str(sample_article.id), "description": "Bremsbeläge", "quantity": 3, "unit_price": 30, "vat_rate": 19}])
        db.refresh(sample_article)
        assert sample_article.stock_quantity == 7  # beim Ausstellen abgebucht
        item = _items(admin_client, inv)[0]
        res = admin_client.post(f"{V1}/{inv['id']}/correction", json={
            "reason": "Rückgabe", "lines": [{"item_id": item["id"], "quantity": 2, "return_to_stock": True}]})
        assert res.status_code == 201, res.text
        db.refresh(sample_article)
        assert sample_article.stock_quantity == 9
        rk_items = _items(admin_client, res.json())
        assert rk_items[0]["returned_to_stock"] is True and Decimal(rk_items[0]["quantity"]) == Decimal("-2")

    def test_ruecknahme_nur_ganze_stueck(self, admin_client, b2b_customer, sample_article):
        inv = _invoice(admin_client, b2b_customer, items=[
            {"article_id": str(sample_article.id), "description": "Bremsbeläge", "quantity": 3, "unit_price": 30, "vat_rate": 19}])
        item = _items(admin_client, inv)[0]
        res = admin_client.post(f"{V1}/{inv['id']}/correction", json={
            "reason": "Rückgabe", "lines": [{"item_id": item["id"], "quantity": 1.5, "return_to_stock": True}]})
        assert res.status_code == 400

    def test_freie_position_nicht_ins_lager(self, admin_client, b2b_customer):
        inv = _invoice(admin_client, b2b_customer)
        item = _items(admin_client, inv)[0]
        res = admin_client.post(f"{V1}/{inv['id']}/correction", json={
            "reason": "Test", "lines": [{"item_id": item["id"], "quantity": 1, "return_to_stock": True}]})
        assert res.status_code == 400 and "kein Lagerartikel" in res.json()["detail"]

    def test_storno_der_korrektur(self, admin_client, db, b2b_customer, sample_article):
        inv = _invoice(admin_client, b2b_customer, items=[
            {"article_id": str(sample_article.id), "description": "Bremsbeläge", "quantity": 3, "unit_price": 30, "vat_rate": 19}])
        item = _items(admin_client, inv)[0]
        rk = admin_client.post(f"{V1}/{inv['id']}/correction", json={
            "reason": "Rückgabe", "lines": [{"item_id": item["id"], "quantity": 2, "return_to_stock": True}]}).json()
        res = admin_client.post(f"{V1}/{rk['id']}/cancel", json={"reason": "Irrtum"})
        assert res.status_code == 200, res.text
        db.refresh(sample_article)
        assert sample_article.stock_quantity == 7  # Rücknahme wieder ausgebucht
        sto = next(i for i in admin_client.get(V1).json() if i["invoice_number"].startswith("STO-"))
        assert Decimal(sto["gross_amount"]) == -Decimal(rk["gross_amount"])  # positiv
        # stornierte Korrektur zählt nicht mehr → volle Menge wieder gutschreibbar
        info = admin_client.get(f"{V1}/{inv['id']}/correction-info").json()
        assert Decimal(info["items"][0]["remaining_quantity"]) == Decimal("3")

    def test_original_mit_korrektur_nicht_stornierbar(self, admin_client, b2b_customer):
        inv = _invoice(admin_client, b2b_customer)
        admin_client.post(f"{V1}/{inv['id']}/correction", json={
            "reason": "Kulanz", "free_lines": [{"description": "x", "net_amount": "1", "vat_rate": 19}]})
        res = admin_client.post(f"{V1}/{inv['id']}/cancel", json={"reason": "Test"})
        assert res.status_code == 400 and "Rechnungskorrektur" in res.json()["detail"]

    def test_stornorechnung_nicht_stornierbar(self, admin_client, b2b_customer):
        inv = _invoice(admin_client, b2b_customer)
        admin_client.post(f"{V1}/{inv['id']}/cancel", json={"reason": "Test"})
        sto = next(i for i in admin_client.get(V1).json() if i["invoice_number"].startswith("STO-"))
        assert admin_client.post(f"{V1}/{sto['id']}/cancel", json={"reason": "x"}).status_code == 400

    def test_erstattung_als_erledigt_markieren(self, admin_client, b2b_customer):
        inv = _invoice(admin_client, b2b_customer, paid=True)
        rk = admin_client.post(f"{V1}/{inv['id']}/correction", json={
            "reason": "Kulanz", "free_lines": [{"description": "x", "net_amount": "1", "vat_rate": 19}]}).json()
        assert admin_client.post(f"{V1}/{rk['id']}/mark-paid").json()["status"] == "paid"


class TestKeineForderung:
    """Storno- und Korrekturbelege sind keine offenen Forderungen (nicht überfällig, keine Mahnung)."""

    def test_nicht_ueberfaellig_und_nicht_mahnbar(self, admin_client, db, b2b_customer):
        from datetime import date, timedelta

        from app.models.invoice import Invoice

        inv = _invoice(admin_client, b2b_customer)
        rk = admin_client.post(f"{V1}/{inv['id']}/correction", json={
            "reason": "Kulanz", "free_lines": [{"description": "x", "net_amount": "1", "vat_rate": 19}]}).json()
        row = db.query(Invoice).filter(Invoice.id == rk["id"]).one()
        row.due_date = date.today() - timedelta(days=30)
        orig = db.query(Invoice).filter(Invoice.id == inv["id"]).one()
        orig.due_date = date.today() + timedelta(days=30)
        db.flush()
        overdue = admin_client.get(f"{V1}?overdue=true").json()
        assert rk["id"] not in [i["id"] for i in overdue]
        assert admin_client.get("/api/v1/dashboard/stats").json()["overdue_invoices"] == 0
        assert admin_client.post(f"{V1}/{rk['id']}/reminder?reminder_level=1").status_code == 400


class TestBelegeUndExport:
    def test_pdf_mit_bezug(self, admin_client, b2b_customer, company_settings):
        from pypdf import PdfReader

        inv = _invoice(admin_client, b2b_customer, paid=True)
        rk = admin_client.post(f"{V1}/{inv['id']}/correction", json={
            "reason": "Kulanz", "free_lines": [{"description": "Kulanznachlass", "net_amount": "10.00", "vat_rate": 19}]}).json()
        text = PdfReader(BytesIO(admin_client.get(f"{V1}/{rk['id']}/pdf").content)).pages[0].extract_text()
        assert "Rechnungskorrektur" in text
        assert f"Zur Rechnung: {inv['invoice_number']} vom 13.10.2026" in text
        assert "11,90" in text and "erstattet" in text
        assert "Fällig" not in text and "Bankverbindung" not in text
        assert "Leistungsdatum: 10.10.2026" in text

    def test_storno_pdf_hat_titel_und_bezug(self, admin_client, b2b_customer, company_settings):
        from pypdf import PdfReader

        inv = _invoice(admin_client, b2b_customer)
        admin_client.post(f"{V1}/{inv['id']}/cancel", json={"reason": "Test"})
        sto = next(i for i in admin_client.get(V1).json() if i["invoice_number"].startswith("STO-"))
        text = PdfReader(BytesIO(admin_client.get(f"{V1}/{sto['id']}/pdf").content)).pages[0].extract_text()
        assert "Stornorechnung" in text and f"Zur Rechnung: {inv['invoice_number']}" in text

    def test_zugferd_gueltig_mit_bezug(self, admin_client, b2b_customer, company_settings):
        from facturx import xml_check_xsd

        inv = _invoice(admin_client, b2b_customer, paid=True)
        arbeit = next(i for i in _items(admin_client, inv) if i["description"] == "Arbeit")
        rk = admin_client.post(f"{V1}/{inv['id']}/correction", json={
            "reason": "Test", "lines": [{"item_id": arbeit["id"], "quantity": 1}],
            "free_lines": [{"description": "Nachlass Buch", "net_amount": "2.00", "vat_rate": 7}]}).json()
        xml = _xml_from_pdf(admin_client.get(f"{V1}/{rk['id']}/zugferd").content)
        assert xml_check_xsd(xml, flavor="factur-x", level="en16931") is True
        assert inv["invoice_number"].encode() in xml        # BT-25
        assert b"Rechnungskorrektur" in xml
        assert b"-0.00" not in xml
        assert b"Zahlbar bis" not in xml

    def test_zugferd_schematron(self, admin_client, b2b_customer, company_settings):
        xslt = os.getenv("EN16931_CII_XSLT")
        saxon = pytest.importorskip("saxonche")
        if not xslt or not os.path.isfile(xslt):
            pytest.skip("EN16931_CII_XSLT nicht gesetzt")
        from lxml import etree

        inv = _invoice(admin_client, b2b_customer, paid=True)
        arbeit = next(i for i in _items(admin_client, inv) if i["description"] == "Arbeit")
        rk = admin_client.post(f"{V1}/{inv['id']}/correction", json={
            "reason": "Test", "lines": [{"item_id": arbeit["id"], "quantity": 1}],
            "free_lines": [{"description": "Nachlass Buch", "net_amount": "2.00", "vat_rate": 7}]}).json()
        xml = _xml_from_pdf(admin_client.get(f"{V1}/{rk['id']}/zugferd").content)
        with saxon.PySaxonProcessor(license=False) as proc:
            exe = proc.new_xslt30_processor().compile_stylesheet(stylesheet_file=xslt)
            out = exe.transform_to_string(xdm_node=proc.parse_xml(xml_text=xml.decode()))
        ns = {"svrl": "http://purl.oclc.org/dsdl/svrl"}
        failed = etree.fromstring(out.encode()).findall(".//svrl:failed-assert", ns)
        assert not failed, [(f.get("id"), f.findtext("svrl:text", namespaces=ns)) for f in failed]

    def test_steuerberater_export(self, admin_client, b2b_customer, company_settings):
        import io
        import zipfile

        inv = _invoice(admin_client, b2b_customer, paid=True)
        admin_client.post(f"{V1}/{inv['id']}/correction", json={
            "reason": "Kulanz", "free_lines": [{"description": "x", "net_amount": "10.00", "vat_rate": 19}]})
        res = admin_client.get("/api/v1/accounting/export?date_from=2026-01-01&date_to=2026-12-31")
        z = zipfile.ZipFile(io.BytesIO(res.content))
        csv = "".join(z.read(n).decode("utf-8-sig") for n in z.namelist() if n.endswith(".csv") and "ausgang" in n.lower())
        assert "Rechnungskorrektur" in csv and "-11,90" in csv
