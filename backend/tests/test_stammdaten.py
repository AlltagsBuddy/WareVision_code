"""Tests: Lieferanten, Lagerorte, Artikelkategorien, Stundensätze, Hersteller/Modelle, Barcode-Suche."""

import pytest

V1 = "/api/v1"


class TestLieferanten:
    def test_crud(self, admin_client):
        res = admin_client.post(f"{V1}/suppliers", json={"name": "Teile Express", "email": "info@teile.test", "city": "Bamberg"})
        assert res.status_code == 201, res.text
        sid = res.json()["id"]
        assert admin_client.get(f"{V1}/suppliers/{sid}").json()["city"] == "Bamberg"
        assert admin_client.patch(f"{V1}/suppliers/{sid}", json={"phone": "0951 1"}).json()["phone"] == "0951 1"
        assert any(s["id"] == sid for s in admin_client.get(f"{V1}/suppliers").json())
        assert admin_client.delete(f"{V1}/suppliers/{sid}").status_code == 204
        assert admin_client.get(f"{V1}/suppliers/{sid}").status_code == 404

    def test_nur_admin_schreibt(self, werkstatt_client):
        assert werkstatt_client.post(f"{V1}/suppliers", json={"name": "X"}).status_code == 403
        assert werkstatt_client.get(f"{V1}/suppliers").status_code == 200


class TestLagerorte:
    def test_crud_und_eindeutigkeit(self, admin_client):
        res = admin_client.post(f"{V1}/storage-locations", json={"name": "Regal B"})
        assert res.status_code == 201
        lid = res.json()["id"]
        assert admin_client.post(f"{V1}/storage-locations", json={"name": "Regal B"}).status_code == 409
        assert admin_client.patch(f"{V1}/storage-locations/{lid}", json={"is_active": False}).json()["is_active"] is False
        assert admin_client.delete(f"{V1}/storage-locations/{lid}").status_code == 204

    def test_loeschen_mit_artikeln_verhindert(self, admin_client, db, sample_article):
        lid = admin_client.post(f"{V1}/storage-locations", json={"name": "Regal C"}).json()["id"]
        sample_article.storage_location_id = lid
        db.flush()
        res = admin_client.delete(f"{V1}/storage-locations/{lid}")
        assert res.status_code == 409
        assert "1 Artikel" in res.json()["detail"]

    def test_leerer_name(self, admin_client):
        assert admin_client.post(f"{V1}/storage-locations", json={"name": ""}).status_code == 422


class TestKategorien:
    def test_crud(self, admin_client):
        cid = admin_client.post(f"{V1}/article-categories", json={"name": "Bremsen"}).json()["id"]
        assert admin_client.post(f"{V1}/article-categories", json={"name": "Bremsen"}).status_code == 409
        assert admin_client.patch(f"{V1}/article-categories/{cid}", json={"description": "Beläge, Scheiben"}).status_code == 200
        assert any(c["name"] == "Bremsen" for c in admin_client.get(f"{V1}/article-categories").json())
        assert admin_client.delete(f"{V1}/article-categories/{cid}").status_code == 204


class TestStundensaetze:
    def test_crud(self, admin_client):
        res = admin_client.post(f"{V1}/labor-rates", json={"name": "Mechaniker", "rate_per_hour": 89, "is_default": True})
        assert res.status_code == 201
        rid = res.json()["id"]
        assert admin_client.patch(f"{V1}/labor-rates/{rid}", json={"rate_per_hour": 95}).json()["rate_per_hour"] == "95.00"
        assert any(r["id"] == rid for r in admin_client.get(f"{V1}/labor-rates").json())
        assert admin_client.delete(f"{V1}/labor-rates/{rid}").status_code == 204

    def test_preis_muss_positiv_sein(self, admin_client):
        assert admin_client.post(f"{V1}/labor-rates", json={"name": "X", "rate_per_hour": 0}).status_code == 422


class TestHersteller:
    def test_hersteller_und_modelle(self, admin_client):
        mid = admin_client.post(f"{V1}/manufacturers", json={"name": "CFMOTO Test"}).json()["id"]
        assert admin_client.post(f"{V1}/manufacturers", json={"name": "CFMOTO Test"}).status_code == 409
        res = admin_client.post(f"{V1}/manufacturers/models", json={"manufacturer_id": mid, "name": "CForce 520", "variant": "L"})
        assert res.status_code == 201
        models = admin_client.get(f"{V1}/manufacturers/{mid}/models").json()
        assert [m["name"] for m in models] == ["CForce 520"]


class TestArtikelBarcode:
    def test_barcode_suche(self, admin_client, sample_article):
        res = admin_client.get(f"{V1}/articles/barcode/4000000000017")
        assert res.status_code == 200
        assert res.json()["article_number"] == "TEST-ART-001"
        assert admin_client.get(f"{V1}/articles/barcode/0000").status_code == 404


class TestReservierungen:
    def test_reservieren_verbrauchen(self, admin_client, sample_article):
        res = admin_client.post(f"{V1}/stock/reservations", json={"article_id": str(sample_article.id), "quantity": 8})
        assert res.status_code == 201
        rid = res.json()["id"]
        # nur noch 2 verfügbar
        res = admin_client.post(f"{V1}/stock/reservations", json={"article_id": str(sample_article.id), "quantity": 3})
        assert res.status_code == 400
        assert "Verfügbar: 2" in res.json()["detail"]
        # Warenausgang über verfügbaren Bestand hinaus verhindert
        res = admin_client.post(f"{V1}/stock/movements", json={"article_id": str(sample_article.id), "movement_type": "outgoing", "quantity": 5})
        assert res.status_code == 400
        assert admin_client.patch(f"{V1}/stock/reservations/{rid}", json={"status": "cancelled"}).json()["status"] == "cancelled"
        assert admin_client.patch(f"{V1}/stock/reservations/{rid}", json={"status": "consumed"}).status_code == 400

    def test_ungueltiger_status(self, admin_client, sample_article):
        rid = admin_client.post(f"{V1}/stock/reservations", json={"article_id": str(sample_article.id), "quantity": 1}).json()["id"]
        assert admin_client.patch(f"{V1}/stock/reservations/{rid}", json={"status": "foo"}).status_code == 400
        assert any(r["id"] == rid for r in admin_client.get(f"{V1}/stock/reservations").json())
