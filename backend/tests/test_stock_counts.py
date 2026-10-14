"""Tests: Inventur (Blindzählung, Differenzbuchung, Abschluss, PDF/CSV)."""

from decimal import Decimal

import pytest

BASE = "/api/v1/stock-counts"


@pytest.fixture()
def articles(db):
    """Drei Artikel, zwei davon im Lagerort „Regal A“, einer inaktiv (darf nicht gezählt werden)."""
    from app.models.article import Article
    from app.models.storage_location import StorageLocation

    loc = StorageLocation(name="Regal A Test")
    db.add(loc)
    db.flush()
    a1 = Article(article_number="INV-T-1", name="Ölfilter", purchase_price=Decimal("4.50"), stock_quantity=10,
                 storage_location_id=loc.id, location_label="Fach 1", barcode="4000000000024")
    a2 = Article(article_number="INV-T-2", name="Zündkerze", purchase_price=Decimal("3.00"), stock_quantity=5,
                 storage_location_id=loc.id)
    a3 = Article(article_number="INV-T-3", name="Luftfilter", purchase_price=Decimal("8.00"), stock_quantity=2)
    inactive = Article(article_number="INV-T-X", name="Ausgelistet", stock_quantity=1, is_active=False)
    db.add_all([a1, a2, a3, inactive])
    db.flush()
    return {"loc": loc, "a1": a1, "a2": a2, "a3": a3, "inactive": inactive}


def _start(client, **payload):
    payload.setdefault("count_date", "2026-12-31")
    return client.post(BASE, json=payload)


def _item(sc, article):
    return next(i for i in sc["items"] if i["article_id"] == str(article.id))


def _count_all(client, sc, values: dict):
    """Ist-Mengen erfassen: values = {article_id: menge}."""
    for item in sc["items"]:
        qty = values.get(item["article_id"])
        res = client.put(f"{BASE}/{sc['id']}/items/{item['id']}", json={"counted_qty": qty})
        assert res.status_code == 200, res.text


class TestAnlegen:
    def test_gesamtes_lager_nur_aktive(self, admin_client, articles):
        res = _start(admin_client)
        assert res.status_code == 201, res.text
        sc = res.json()
        ids = {i["article_id"] for i in sc["items"]}
        assert str(articles["inactive"].id) not in ids
        assert {str(articles[k].id) for k in ("a1", "a2", "a3")} <= ids
        assert sc["scope_label"] == "Gesamtes Lager"
        assert sc["count_number"] == "INV-2026-01"

    def test_teilinventur_lagerort(self, admin_client, articles):
        sc = _start(admin_client, storage_location_id=str(articles["loc"].id)).json()
        assert sc["total_items"] == 2
        assert "Regal A Test" in sc["scope_label"]
        assert _item(sc, articles["a1"])["location"] == "Regal A Test / Fach 1"

    def test_nur_eine_offene_inventur(self, admin_client, articles):
        assert _start(admin_client).status_code == 201
        assert _start(admin_client).status_code == 400

    def test_nur_admin(self, werkstatt_client, articles):
        assert _start(werkstatt_client).status_code == 403

    def test_blindzaehlung_soll_erst_nach_eingabe(self, admin_client, articles):
        sc = _start(admin_client).json()
        item = _item(sc, articles["a1"])
        assert item["expected_qty"] is None
        assert item["counted_qty"] is None


class TestZaehlen:
    def test_negativ_abgelehnt(self, admin_client, articles):
        sc = _start(admin_client).json()
        res = admin_client.put(f"{BASE}/{sc['id']}/items/{_item(sc, articles['a1'])['id']}", json={"counted_qty": -1})
        assert res.status_code == 422

    def test_werkstatt_darf_zaehlen(self, admin_client, werkstatt_user, articles):
        from app.core.security import create_access_token

        sc = _start(admin_client).json()
        item = _item(sc, articles["a1"])
        # Admin- und Werkstatt-Client teilen sich denselben TestClient → Token wechseln
        admin_client.headers["Authorization"] = f"Bearer {create_access_token(str(werkstatt_user.id))}"
        res = admin_client.put(f"{BASE}/{sc['id']}/items/{item['id']}", json={"counted_qty": 9, "note": "Karton offen"})
        assert res.status_code == 200
        assert res.json()["expected_qty"] == 10
        assert res.json()["note"] == "Karton offen"

    def test_zuruecksetzen(self, admin_client, articles):
        sc = _start(admin_client).json()
        item = _item(sc, articles["a1"])
        admin_client.put(f"{BASE}/{sc['id']}/items/{item['id']}", json={"counted_qty": 9})
        res = admin_client.put(f"{BASE}/{sc['id']}/items/{item['id']}", json={"counted_qty": None})
        assert res.json()["counted_qty"] is None
        assert res.json()["expected_qty"] is None

    def test_abschluss_erst_wenn_alles_gezaehlt(self, admin_client, articles):
        sc = _start(admin_client).json()
        res = admin_client.post(f"{BASE}/{sc['id']}/complete")
        assert res.status_code == 400
        assert "nicht gezählt" in res.json()["detail"]


class TestAbschluss:
    def test_differenzen_werden_gebucht(self, admin_client, db, articles):
        a1, a2, a3 = articles["a1"], articles["a2"], articles["a3"]
        sc = _start(admin_client, storage_location_id=None).json()
        values = {i["article_id"]: None for i in sc["items"]}
        # alle übrigen Artikel unverändert zählen
        from app.models.article import Article
        for aid in values:
            values[aid] = db.query(Article).filter(Article.id == aid).first().stock_quantity
        values[str(a1.id)] = 13   # +3 Mehrbestand
        values[str(a2.id)] = 3    # -2 Fehlbestand
        values[str(a3.id)] = 2    # passt
        _count_all(admin_client, sc, values)

        res = admin_client.post(f"{BASE}/{sc['id']}/complete")
        assert res.status_code == 200, res.text
        done = res.json()
        assert done["status"] == "completed"
        assert _item(done, a1)["difference"] == 3
        assert _item(done, a2)["difference"] == -2
        assert _item(done, a3)["difference"] == 0
        for a in (a1, a2, a3):
            db.refresh(a)
        assert (a1.stock_quantity, a2.stock_quantity, a3.stock_quantity) == (13, 3, 2)
        # Lagerwert zum EK: Differenz = +3*4,50 - 2*3,00 = +7,50
        assert Decimal(done["value_counted"]) - Decimal(done["value_expected"]) == Decimal("7.50")

        moves = admin_client.get(f"/api/v1/stock/movements?article_id={a1.id}").json()
        assert any("Inventur INV-2026-01" in (m["notes"] or "") and m["movement_type"] == "incoming" for m in moves)
        moves = admin_client.get(f"/api/v1/stock/movements?article_id={a2.id}").json()
        assert any(m["movement_type"] == "correction" and m["quantity"] == 2 for m in moves)

    def test_buchung_nach_zaehlung_bleibt_erhalten(self, admin_client, db, articles):
        """Verkauf nach der Zählung: die Inventurdifferenz wird relativ gebucht, der Verkauf bleibt."""
        a1 = articles["a1"]
        sc = _start(admin_client, storage_location_id=str(articles["loc"].id)).json()
        _count_all(admin_client, sc, {str(a1.id): 12, str(articles["a2"].id): 5})
        admin_client.post("/api/v1/stock/movements", json={"article_id": str(a1.id), "movement_type": "outgoing", "quantity": 1})
        assert admin_client.post(f"{BASE}/{sc['id']}/complete").status_code == 200
        db.refresh(a1)
        assert a1.stock_quantity == 12 - 1  # Inventur +2 auf 12, danach Verkauf -1

    def test_buchung_vor_zaehlung_im_soll(self, admin_client, articles):
        """Wareneingang vor der Zählung: das Soll enthält ihn bereits (keine falsche Differenz)."""
        a1 = articles["a1"]
        sc = _start(admin_client, storage_location_id=str(articles["loc"].id)).json()
        admin_client.post("/api/v1/stock/movements", json={"article_id": str(a1.id), "movement_type": "incoming", "quantity": 5})
        res = admin_client.put(f"{BASE}/{sc['id']}/items/{_item(sc, a1)['id']}", json={"counted_qty": 15})
        assert res.json()["expected_qty"] == 15

    def test_abgeschlossen_unveraenderbar(self, admin_client, articles):
        sc = _start(admin_client, storage_location_id=str(articles["loc"].id)).json()
        _count_all(admin_client, sc, {str(articles["a1"].id): 10, str(articles["a2"].id): 5})
        admin_client.post(f"{BASE}/{sc['id']}/complete")
        item = _item(sc, articles["a1"])
        assert admin_client.put(f"{BASE}/{sc['id']}/items/{item['id']}", json={"counted_qty": 1}).status_code == 400
        assert admin_client.post(f"{BASE}/{sc['id']}/cancel").status_code == 400
        assert admin_client.post(f"{BASE}/{sc['id']}/complete").status_code == 400

    def test_abbrechen_bucht_nichts(self, admin_client, db, articles):
        sc = _start(admin_client, storage_location_id=str(articles["loc"].id)).json()
        _count_all(admin_client, sc, {str(articles["a1"].id): 0, str(articles["a2"].id): 0})
        assert admin_client.post(f"{BASE}/{sc['id']}/cancel").json()["status"] == "cancelled"
        db.refresh(articles["a1"])
        assert articles["a1"].stock_quantity == 10
        # danach kann eine neue Inventur starten
        assert _start(admin_client).status_code == 201


class TestAusgabe:
    def test_zaehlliste_ohne_soll(self, admin_client, articles):
        from io import BytesIO
        from pypdf import PdfReader

        sc = _start(admin_client, storage_location_id=str(articles["loc"].id)).json()
        res = admin_client.get(f"{BASE}/{sc['id']}/pdf")
        assert res.status_code == 200
        text = PdfReader(BytesIO(res.content)).pages[0].extract_text()
        assert "Zählliste" in text
        assert "Soll" not in text  # Blindzählung

    def test_inventurliste_und_csv(self, admin_client, articles):
        from io import BytesIO
        from pypdf import PdfReader

        sc = _start(admin_client, storage_location_id=str(articles["loc"].id)).json()
        _count_all(admin_client, sc, {str(articles["a1"].id): 10, str(articles["a2"].id): 4})
        admin_client.post(f"{BASE}/{sc['id']}/complete")
        text = PdfReader(BytesIO(admin_client.get(f"{BASE}/{sc['id']}/pdf").content)).pages[0].extract_text()
        assert "Inventurliste" in text and "Lagerwert laut Inventur" in text
        csv = admin_client.get(f"{BASE}/{sc['id']}/csv").content.decode("utf-8-sig")
        assert "INV-T-2;Zündkerze" in csv
        assert ";5;4;-1;3,00;12,00;" in csv
        assert "Lagerwert laut Inventur" in csv

    def test_liste_mit_fortschritt(self, admin_client, articles):
        sc = _start(admin_client, storage_location_id=str(articles["loc"].id)).json()
        admin_client.put(f"{BASE}/{sc['id']}/items/{sc['items'][0]['id']}", json={"counted_qty": 1})
        row = next(x for x in admin_client.get(BASE).json() if x["id"] == sc["id"])
        assert (row["counted_items"], row["total_items"]) == (1, 2)
