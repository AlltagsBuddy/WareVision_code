"""Tests: Lieferanten-Artikeldaten (Import CSV/Excel, E-Rechnungs-Positionen, Etikett-Foto mit KI)."""

import io
import json

import pytest

from tests.test_einvoice import UBL, _create_invoice, _xml_from_pdf, MIXED

API = "/api/v1/article-catalog"
INC = "/api/v1/incoming-invoices"

CSV = (
    "Artikel-Nr.;EAN;Bezeichnung;Hersteller;Herstellernummer;EK netto;UVP;MwSt\n"
    "NGK-1;4006381333931;Zündkerze CR7HSA;NGK;4549;3,95;8,90;19\n"
    "BR-2;;Bremsbelag vorne;EBC;FA197;12,50;;19\n"
    ";;Zeile ohne Nummer;;;;;\n"
).encode("cp1252")


def _upload(client, path, content=CSV, name="lieferant.csv", **form):
    return client.post(f"{API}{path}", files={"file": (name, content, "text/csv")}, data=form)


def _import(client, content=CSV, name="lieferant.csv", supplier_name="Teile Gross GmbH"):
    prev = _upload(client, "/import/preview", content, name).json()
    res = _upload(client, "/import", content, name, mapping=json.dumps(prev["mapping"]), supplier_name=supplier_name)
    assert res.status_code == 200, res.text
    return prev, res.json()


class TestImport:
    def test_vorschau_erkennt_spalten(self, admin_client):
        prev = _upload(admin_client, "/import/preview").json()
        h = prev["headers"]
        m = prev["mapping"]
        assert h[m["barcode"]] == "EAN" and h[m["name"]] == "Bezeichnung"
        assert h[m["supplier_article_number"]] == "Artikel-Nr." and h[m["purchase_price"]] == "EK netto"
        assert h[m["retail_price_gross"]] == "UVP" and prev["row_count"] == 3
        assert prev["sample"][0][2] == "Zündkerze CR7HSA"  # Windows-Zeichensatz korrekt gelesen

    def test_import_und_scan_vorschlag(self, admin_client):
        _, res = _import(admin_client)
        assert (res["created"], res["updated"], res["skipped"]) == (2, 0, 1)
        hits = admin_client.get(f"{API}/lookup", params={"barcode": "4006381333931"}).json()
        assert len(hits) == 1
        h = hits[0]
        assert (h["name"], h["manufacturer"], h["supplier_article_number"]) == ("Zündkerze CR7HSA", "NGK", "NGK-1")
        assert h["purchase_price"] == 3.95 and h["retail_price_net"] == 7.48  # 8,90 brutto → netto
        assert h["manufacturer_part_number"] == "4549"

    def test_erneuter_import_aktualisiert(self, admin_client):
        _import(admin_client)
        _, res = _import(admin_client, CSV.replace(b"3,95", b"4,10"))
        assert (res["created"], res["updated"]) == (0, 2)
        assert admin_client.get(f"{API}/lookup", params={"barcode": "4006381333931"}).json()[0]["purchase_price"] == 4.1

    def test_excel(self, admin_client):
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.append(["Bestellnummer", "GTIN", "Artikelbezeichnung", "Händlerpreis"])
        ws.append(["X-9", 4006381333948, "Luftfilter", 19.9])
        buf = io.BytesIO()
        wb.save(buf)
        _, res = _import(admin_client, buf.getvalue(), "daten.xlsx")
        assert res["created"] == 1
        hit = admin_client.get(f"{API}/lookup", params={"barcode": "4006381333948"}).json()[0]
        assert hit["name"] == "Luftfilter" and hit["purchase_price"] == 19.9

    def test_suche_und_quellen_und_loeschen(self, admin_client):
        _import(admin_client)
        assert [h["supplier_article_number"] for h in admin_client.get(f"{API}/search", params={"q": "FA197"}).json()] == ["BR-2"]
        src = admin_client.get(f"{API}/sources").json()
        assert src == [{**src[0], "supplier_name": "Teile Gross GmbH", "source": "import", "count": 2}]
        assert admin_client.delete(API, params={"supplier_name": "Teile Gross GmbH"}).json()["deleted"] == 2
        assert admin_client.get(f"{API}/lookup", params={"barcode": "4006381333931"}).json() == []

    def test_ohne_bezeichnung_abgelehnt(self, admin_client):
        res = _upload(admin_client, "/import", mapping=json.dumps({"barcode": 1}), supplier_name="X")
        assert res.status_code == 422 and "Bezeichnung" in res.json()["detail"]

    def test_altes_excel_klare_meldung(self, admin_client):
        res = _upload(admin_client, "/import/preview", b"\xd0\xcf\x11\xe0", "alt.xls")
        assert res.status_code == 422 and ".xlsx" in res.json()["detail"]

    def test_rechte(self, werkstatt_client):
        # Werkstatt darf nachschlagen, aber ohne „Lager & Einkauf“ nichts importieren
        assert werkstatt_client.get(f"{API}/lookup", params={"barcode": "1"}).status_code == 200
        assert _upload(werkstatt_client, "/import/preview").status_code == 403


UBL_EAN = UBL.replace(
    b"<cac:Item><cbc:Name>Bremsbelag</cbc:Name>",
    b"<cac:Item><cbc:Name>Bremsbelag</cbc:Name><cac:SellersItemIdentification><cbc:ID>MT-77</cbc:ID>"
    b"</cac:SellersItemIdentification><cac:StandardItemIdentification><cbc:ID schemeID=\"0160\">4006381333955</cbc:ID>"
    b"</cac:StandardItemIdentification>",
)


class TestERechnung:
    def test_ubl_positionen_werden_vorschlaege(self, admin_client):
        res = admin_client.post(f"{INC}/import-einvoice", files={"file": ("r.xml", UBL_EAN, "application/xml")})
        assert res.status_code == 201, res.text
        hit = admin_client.get(f"{API}/lookup", params={"barcode": "4006381333955"}).json()
        assert len(hit) == 1
        assert (hit[0]["name"], hit[0]["supplier_name"], hit[0]["supplier_article_number"], hit[0]["purchase_price"]) == (
            "Bremsbelag", "Moto Teile AG", "MT-77", 70.0)
        assert hit[0]["source"] == "einvoice" and hit[0]["source_ref"] == "UBL-4711"

    def test_cii_mit_gtin(self, admin_client, b2b_customer, company_settings):
        out = _create_invoice(admin_client, b2b_customer.id, MIXED[:1])
        xml = _xml_from_pdf(admin_client.get(f"/api/v1/invoices/{out['id']}/zugferd").content)
        xml = xml.replace(b"<ram:SpecifiedTradeProduct>", b"<ram:SpecifiedTradeProduct><ram:GlobalID schemeID=\"0160\">"
                          b"4006381333962</ram:GlobalID><ram:SellerAssignedID>CII-1</ram:SellerAssignedID>", 1)
        res = admin_client.post(f"{INC}/import-einvoice", files={"file": ("c.xml", xml, "application/xml")})
        assert res.status_code == 201, res.text
        hit = admin_client.get(f"{API}/lookup", params={"barcode": "4006381333962"}).json()
        assert len(hit) == 1 and hit[0]["supplier_article_number"] == "CII-1"

    def test_ohne_kennung_kein_vorschlag_und_nachtraeglich(self, admin_client, db):
        from app.models.supplier_catalog import SupplierCatalogItem
        inv = admin_client.post(f"{INC}/import-einvoice", files={"file": ("r.xml", UBL, "application/xml")}).json()
        assert db.query(SupplierCatalogItem).count() == 0
        res = admin_client.post(f"{INC}/{inv['id']}/positions-to-catalog")
        assert res.status_code == 200 and res.json()["skipped"] == 1

    def test_manuelle_rechnung_nicht_moeglich(self, admin_client):
        inv = admin_client.post(INC, json={"supplier_name": "X", "invoice_number": "1", "invoice_date": "2026-10-01",
                                           "net_amount": 10, "gross_amount": 11.9}).json()
        assert admin_client.post(f"{INC}/{inv['id']}/positions-to-catalog").status_code == 400


class TestEtikettFoto:
    @pytest.fixture()
    def ai_key(self, db):
        from app.models.app_setting import AppSetting
        db.add(AppSetting(key="ai_help_api_key", value="test-key"))
        db.flush()

    @staticmethod
    def _png():
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (40, 20), "white").save(buf, format="PNG")
        return buf.getvalue()

    def test_ohne_ki_klare_meldung(self, admin_client):
        assert admin_client.get(f"{API}/recognize-label/status").json() == {"enabled": False}
        res = admin_client.post(f"{API}/recognize-label", files={"file": ("e.png", self._png(), "image/png")})
        assert res.status_code == 400 and "nicht eingerichtet" in res.json()["detail"]

    def test_vorschlag_aus_foto(self, admin_client, ai_key, monkeypatch):
        from app.services import label_recognition
        sent = {}

        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def fake_urlopen(req, timeout):
            sent["body"] = json.loads(req.data)
            sent["key"] = req.headers.get("X-api-key")
            answer = {"content": [{"type": "text", "text": "```json\n" + json.dumps({
                "name": "Zündkerze", "manufacturer": "NGK", "manufacturer_part_number": "CR7HSA",
                "barcode": "4006381333931", "description": None}) + "\n```"}]}
            return Resp(json.dumps(answer).encode())

        monkeypatch.setattr(label_recognition.urllib.request, "urlopen", fake_urlopen)
        _import(admin_client)
        res = admin_client.post(f"{API}/recognize-label", files={"file": ("e.png", self._png(), "image/png")})
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["suggestion"]["manufacturer"] == "NGK" and body["suggestion"]["barcode"] == "4006381333931"
        assert body["catalog"][0]["supplier_article_number"] == "NGK-1"  # Barcode zusätzlich im Katalog gefunden
        content = sent["body"]["messages"][0]["content"]
        assert content[0]["type"] == "image" and content[0]["source"]["media_type"] == "image/jpeg"
        assert sent["key"] == "test-key"

    def test_kein_etikett(self, admin_client, ai_key, monkeypatch):
        from app.services import label_recognition
        monkeypatch.setattr(label_recognition, "recognize",
                            lambda *a: (_ for _ in ()).throw(label_recognition.LabelError("kein lesbares Etikett")))
        res = admin_client.post(f"{API}/recognize-label", files={"file": ("e.png", self._png(), "image/png")})
        assert res.status_code == 422

    def test_antwort_pruefen(self):
        from app.services.label_recognition import LabelError, _parse_answer
        out = _parse_answer('{"name": "Ölfilter", "barcode": "12AB", "manufacturer": null}')
        assert out["name"] == "Ölfilter" and out["barcode"] is None and out["manufacturer"] is None
        with pytest.raises(LabelError):
            _parse_answer("Ich sehe kein Etikett.")
