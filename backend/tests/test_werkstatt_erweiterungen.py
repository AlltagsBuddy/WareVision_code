"""Tests: Wartungsplan nach Baujahr, Teile-Hersteller, Auftragsfotos, Suche, Storno → neue Rechnung."""

import io
import struct
import zlib
from datetime import date

import pytest

API = "/api/v1"


def _png_bytes() -> bytes:
    """Kleines gültiges PNG (1x1 Pixel)."""
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw = b"\x00\xff\x00\x00"
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


@pytest.fixture()
def upload_tmp(tmp_path, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "UPLOAD_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture()
def order(db, sample_customer, sample_vehicle, admin_user):
    from app.models.workshop_order import WorkshopOrder
    o = WorkshopOrder(customer_id=sample_customer.id, vehicle_id=sample_vehicle.id,
                      order_number="WO-TEST-0001", status="in_progress", created_by=admin_user.id)
    db.add(o)
    db.flush()
    return o


# ---------------------------------------------------------------------------
# Wartungsplan nach Baujahr
# ---------------------------------------------------------------------------

class TestWartungsplanBaujahr:
    def _plan(self, client, manufacturer_id, name, **extra):
        res = client.post(f"{API}/maintenance-plans", json={"manufacturer_id": str(manufacturer_id), "name": name, **extra})
        assert res.status_code == 201, res.text
        return res.json()

    def test_baujahr_speichern_und_pruefen(self, admin_client, sample_manufacturer):
        p = self._plan(admin_client, sample_manufacturer.id, "Alt", build_year_from=2000, build_year_to=2012)
        assert (p["build_year_from"], p["build_year_to"]) == (2000, 2012)
        bad = admin_client.post(f"{API}/maintenance-plans", json={
            "manufacturer_id": str(sample_manufacturer.id), "name": "Falsch", "build_year_from": 2015, "build_year_to": 2010})
        assert bad.status_code == 422

    def test_aendern_und_leeren(self, admin_client, sample_manufacturer):
        p = self._plan(admin_client, sample_manufacturer.id, "Plan", build_year_to=2012)
        res = admin_client.patch(f"{API}/maintenance-plans/{p['id']}", json={"build_year_from": 2005})
        assert (res.json()["build_year_from"], res.json()["build_year_to"]) == (2005, 2012)
        res = admin_client.patch(f"{API}/maintenance-plans/{p['id']}", json={"build_year_from": 2020})
        assert res.status_code == 400
        res = admin_client.patch(f"{API}/maintenance-plans/{p['id']}", json={"build_year_to": None})
        assert res.status_code == 200 and res.json()["build_year_to"] is None
        assert res.json()["build_year_from"] == 2005

    def test_passender_plan_nach_baujahr(self, admin_client, db, sample_manufacturer, sample_vehicle):
        from app.models.manufacturer import VehicleModel
        model = VehicleModel(manufacturer_id=sample_manufacturer.id, name="Modell X")
        db.add(model)
        db.flush()
        self._plan(admin_client, sample_manufacturer.id, "Hersteller allgemein")
        self._plan(admin_client, sample_manufacturer.id, "Modell alle Jahre", vehicle_model_id=str(model.id))
        self._plan(admin_client, sample_manufacturer.id, "Modell alt", vehicle_model_id=str(model.id), build_year_to=2012)
        self._plan(admin_client, sample_manufacturer.id, "Modell neu", vehicle_model_id=str(model.id), build_year_from=2013)

        def found():
            return admin_client.get(f"{API}/maintenance-plans/for-vehicle/{sample_vehicle.id}").json()

        # ohne Modell → Herstellerplan
        assert found()["name"] == "Hersteller allgemein"
        sample_vehicle.vehicle_model_id = model.id
        # Baujahr unbekannt → nur Plan ohne Bereich
        assert found()["name"] == "Modell alle Jahre"
        sample_vehicle.build_year = 2008
        db.flush()
        assert found()["name"] == "Modell alt"
        sample_vehicle.build_year = 2019
        db.flush()
        assert found()["name"] == "Modell neu"

    def test_altes_fahrzeug_ohne_modellplan(self, admin_client, db, sample_manufacturer, sample_vehicle):
        self._plan(admin_client, sample_manufacturer.id, "Bis 2010", build_year_to=2010)
        self._plan(admin_client, sample_manufacturer.id, "Ab 2011", build_year_from=2011)
        sample_vehicle.build_year = 2004
        db.flush()
        assert admin_client.get(f"{API}/maintenance-plans/for-vehicle/{sample_vehicle.id}").json()["name"] == "Bis 2010"
        sample_vehicle.build_year = None
        db.flush()
        assert admin_client.get(f"{API}/maintenance-plans/for-vehicle/{sample_vehicle.id}").json() is None

    def test_auftrag_uebernimmt_plan_nach_baujahr(self, admin_client, db, sample_customer, sample_manufacturer, sample_vehicle):
        self._plan(admin_client, sample_manufacturer.id, "Neu", build_year_from=2015)
        alt = self._plan(admin_client, sample_manufacturer.id, "Alt", build_year_to=2014)
        sample_vehicle.build_year = 2009
        db.flush()
        res = admin_client.post(f"{API}/workshop-orders", json={
            "customer_id": str(sample_customer.id), "vehicle_id": str(sample_vehicle.id)})
        assert res.status_code == 201
        assert res.json()["maintenance_plan_id"] == alt["id"]


# ---------------------------------------------------------------------------
# Teile-Hersteller und passende Artikel
# ---------------------------------------------------------------------------

class TestTeileHersteller:
    def test_hersteller_speichern_suchen_und_modellfilter(self, admin_client, db, sample_manufacturer):
        from app.models.manufacturer import VehicleModel
        m1 = VehicleModel(manufacturer_id=sample_manufacturer.id, name="A")
        m2 = VehicleModel(manufacturer_id=sample_manufacturer.id, name="B")
        db.add_all([m1, m2])
        db.flush()
        res = admin_client.post(f"{API}/articles", json={
            "article_number": "ZK-1", "name": "Zündkerze", "purchase_price": 3.5, "sales_price_b2c": 7,
            "sales_price_b2b": 6, "part_manufacturer": "NGK", "compatible_model_ids": [str(m1.id)]})
        assert res.status_code == 201, res.text
        art = res.json()
        assert art["part_manufacturer"] == "NGK" and float(art["purchase_price"]) == 3.5
        admin_client.post(f"{API}/articles", json={
            "article_number": "OEL-1", "name": "Öl", "sales_price_b2c": 10, "sales_price_b2b": 9,
            "compatible_model_ids": [str(m2.id)]})

        found = admin_client.get(f"{API}/articles", params={"search": "ngk"}).json()
        assert [a["article_number"] for a in found] == ["ZK-1"]
        fits = admin_client.get(f"{API}/articles", params={"vehicle_model_id": str(m1.id)}).json()
        assert [a["article_number"] for a in fits] == ["ZK-1"]

        res = admin_client.patch(f"{API}/articles/{art['id']}", json={"part_manufacturer": "Bosch"})
        assert res.json()["part_manufacturer"] == "Bosch"


# ---------------------------------------------------------------------------
# Fotos am Auftrag
# ---------------------------------------------------------------------------

class TestAuftragsfotos:
    def test_hochladen_anzeigen_loeschen(self, admin_client, order, upload_tmp):
        png = _png_bytes()
        res = admin_client.post(f"{API}/workshop-orders/{order.id}/photos",
                                files={"file": ("schaden.png", io.BytesIO(png), "image/png")},
                                data={"caption": "Kratzer vorne"})
        assert res.status_code == 201, res.text
        photo = res.json()
        assert photo["caption"] == "Kratzer vorne" and photo["content_type"] == "image/png"
        assert list((upload_tmp / "werkstattfotos" / str(order.id)).iterdir())

        lst = admin_client.get(f"{API}/workshop-orders/{order.id}/photos").json()
        assert [p["id"] for p in lst] == [photo["id"]]
        img = admin_client.get(f"{API}/workshop-orders/{order.id}/photos/{photo['id']}")
        assert img.status_code == 200 and img.content == png

        res = admin_client.patch(f"{API}/workshop-orders/{order.id}/photos/{photo['id']}", json={"caption": "Neu"})
        assert res.json()["caption"] == "Neu"

        assert admin_client.delete(f"{API}/workshop-orders/{order.id}/photos/{photo['id']}").status_code == 204
        assert admin_client.get(f"{API}/workshop-orders/{order.id}/photos").json() == []
        assert not list((upload_tmp / "werkstattfotos" / str(order.id)).iterdir())

    def test_falscher_dateityp_abgelehnt(self, admin_client, order, upload_tmp):
        # Endung und Typ behaupten Bild, Inhalt ist keins
        res = admin_client.post(f"{API}/workshop-orders/{order.id}/photos",
                                files={"file": ("x.jpg", io.BytesIO(b"<script>alert(1)</script>"), "image/jpeg")})
        assert res.status_code == 400
        assert "JPEG" in res.json()["detail"]

    def test_foto_anderer_auftrag_nicht_abrufbar(self, admin_client, db, order, upload_tmp, sample_customer, sample_vehicle, admin_user):
        from app.models.workshop_order import WorkshopOrder
        other = WorkshopOrder(customer_id=sample_customer.id, vehicle_id=sample_vehicle.id,
                              order_number="WO-TEST-0002", status="new", created_by=admin_user.id)
        db.add(other)
        db.flush()
        photo = admin_client.post(f"{API}/workshop-orders/{order.id}/photos",
                                  files={"file": ("a.png", io.BytesIO(_png_bytes()), "image/png")}).json()
        assert admin_client.get(f"{API}/workshop-orders/{other.id}/photos/{photo['id']}").status_code == 404

    def test_dsgvo_anonymisierung_loescht_fotos(self, admin_client, order, upload_tmp, sample_customer):
        admin_client.post(f"{API}/workshop-orders/{order.id}/photos",
                          files={"file": ("a.png", io.BytesIO(_png_bytes()), "image/png")})
        res = admin_client.post(f"{API}/customers/{sample_customer.id}/dsgvo-delete")
        assert res.json()["action"] == "anonymized"
        assert admin_client.get(f"{API}/workshop-orders/{order.id}/photos").json() == []
        assert not list((upload_tmp / "werkstattfotos" / str(order.id)).iterdir())


# ---------------------------------------------------------------------------
# Suche
# ---------------------------------------------------------------------------

class TestSuche:
    def test_eingangsrechnungen_suchen(self, admin_client):
        for supplier, number in (("Motorrad Teile GmbH", "ER-100"), ("Ölhandel Meier", "ER-200")):
            res = admin_client.post(f"{API}/incoming-invoices", json={
                "supplier_name": supplier, "invoice_number": number, "invoice_date": str(date.today()),
                "net_amount": 100, "vat_amount": 19, "gross_amount": 119})
            assert res.status_code == 201, res.text
        assert [i["invoice_number"] for i in admin_client.get(f"{API}/incoming-invoices", params={"search": "meier"}).json()] == ["ER-200"]
        assert [i["supplier_name"] for i in admin_client.get(f"{API}/incoming-invoices", params={"search": "ER-100"}).json()] == ["Motorrad Teile GmbH"]

    def test_audit_log_suchen(self, admin_client, db, admin_user):
        from app.services.audit import log_audit
        log_audit(db, user_id=admin_user.id, entity_type="article", action="update", new_values={"name": "Kettensatz XY"})
        log_audit(db, user_id=None, entity_type="invoice", action="issue")
        db.flush()
        hits = admin_client.get(f"{API}/audit-logs", params={"search": "kettensatz"}).json()
        assert len(hits) == 1 and hits[0]["entity_type"] == "article"
        by_user = admin_client.get(f"{API}/audit-logs", params={"search": admin_user.email}).json()
        assert by_user and all(h["user_id"] == str(admin_user.id) for h in by_user)


# ---------------------------------------------------------------------------
# Storno → Auftrag bearbeiten → neue Rechnung
# ---------------------------------------------------------------------------

class TestStornoUndNeueRechnung:
    def test_ablauf(self, admin_client, db, order, sample_customer, sample_article, company_settings):
        res = admin_client.post(f"{API}/workshop-orders/{order.id}/items", json={
            "item_type": "material", "article_id": str(sample_article.id), "description": "Bremsbeläge",
            "quantity": 2, "unit_price": 35})
        assert res.status_code == 201, res.text
        db.refresh(sample_article)
        assert sample_article.stock_quantity == 8

        inv = admin_client.post(f"{API}/invoices", json={
            "customer_id": str(sample_customer.id), "workshop_order_id": str(order.id),
            "invoice_date": str(date.today())}).json()
        assert admin_client.post(f"{API}/invoices/{inv['id']}/issue").status_code == 200
        assert admin_client.get(f"{API}/workshop-orders/{order.id}").json()["status"] == "invoiced"
        # Abgerechneter Auftrag ist gesperrt
        locked = admin_client.post(f"{API}/workshop-orders/{order.id}/items", json={
            "item_type": "labor", "description": "Arbeit", "quantity": 1, "unit_price": 50})
        assert locked.status_code == 400

        assert admin_client.post(f"{API}/invoices/{inv['id']}/cancel", json={"reason": "falsche Menge"}).status_code == 200
        assert admin_client.get(f"{API}/workshop-orders/{order.id}").json()["status"] == "completed"
        db.refresh(sample_article)
        assert sample_article.stock_quantity == 8  # Material bleibt am Auftrag gebucht

        # Auftrag korrigieren: Position entfernen (Bestand zurück), neue Position hinzufügen
        item_id = admin_client.get(f"{API}/workshop-orders/{order.id}/items").json()[0]["id"]
        assert admin_client.delete(f"{API}/workshop-orders/{order.id}/items/{item_id}").status_code == 204
        db.refresh(sample_article)
        assert sample_article.stock_quantity == 10
        admin_client.post(f"{API}/workshop-orders/{order.id}/items", json={
            "item_type": "material", "article_id": str(sample_article.id), "description": "Bremsbeläge",
            "quantity": 1, "unit_price": 35})
        db.refresh(sample_article)
        assert sample_article.stock_quantity == 9

        new = admin_client.post(f"{API}/invoices", json={
            "customer_id": str(sample_customer.id), "workshop_order_id": str(order.id),
            "invoice_date": str(date.today())})
        assert new.status_code == 201, new.text
        assert new.json()["invoice_number"] != inv["invoice_number"]
        assert float(new.json()["net_amount"]) == 35.0
        assert admin_client.get(f"{API}/workshop-orders/{order.id}").json()["status"] == "invoiced"
