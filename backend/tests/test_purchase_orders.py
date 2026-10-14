"""Tests: Bestellwesen – Bestellvorschlag, Bestellung, PDF, E-Mail, Wareneingang, Storno."""

from decimal import Decimal

import pytest

V1 = "/api/v1"
BASE = f"{V1}/purchase-orders"


@pytest.fixture()
def supplier(db):
    """Lieferant mit E-Mail und Kundennummer."""
    from app.models.supplier import Supplier

    s = Supplier(name="Quad Teile GmbH", email="bestellung@quadteile.de", street="Hauptstraße", house_number="1",
                 postal_code="96047", city="Bamberg", contact_person="Frau Meier", customer_number="K-4711")
    db.add(s)
    db.flush()
    return s


@pytest.fixture()
def articles(db, supplier):
    """Drei Artikel: unter Mindestbestand (mit Zielbestand), unter Mindestbestand ohne Lieferant, ausreichend."""
    from app.models.article import Article

    a1 = Article(article_number="ZK-001", name="Zündkerze", supplier_id=supplier.id, supplier_article_number="NGK-CR7",
                 purchase_price=Decimal("4.50"), sales_price_b2c=Decimal("9.90"), sales_price_b2b=Decimal("8"),
                 vat_rate=Decimal("19"), stock_quantity=1, minimum_stock=3, target_stock=10)
    a2 = Article(article_number="OEL-001", name="Motoröl 1 l", purchase_price=Decimal("6.00"),
                 sales_price_b2c=Decimal("12"), sales_price_b2b=Decimal("10"), vat_rate=Decimal("19"),
                 stock_quantity=0, minimum_stock=4)
    a3 = Article(article_number="FIL-001", name="Luftfilter", supplier_id=supplier.id, purchase_price=Decimal("8"),
                 sales_price_b2c=Decimal("15"), sales_price_b2b=Decimal("13"), vat_rate=Decimal("19"),
                 stock_quantity=5, minimum_stock=2, target_stock=6)
    db.add_all([a1, a2, a3])
    db.flush()
    return a1, a2, a3


def _order_payload(supplier, a1, qty=9, price="4.50"):
    return {
        "supplier_id": str(supplier.id),
        "order_date": "2026-10-14",
        "expected_date": "2026-10-20",
        "items": [
            {"article_id": str(a1.id), "description": a1.name, "quantity": qty, "unit_price": price, "vat_rate": 19},
            {"description": "Versandkosten", "quantity": 1, "unit_price": "5.95", "vat_rate": 19},
        ],
    }


@pytest.fixture()
def order(admin_client, supplier, articles):
    res = admin_client.post(BASE, json=_order_payload(supplier, articles[0]))
    assert res.status_code == 201, res.text
    return res.json()


class TestBestellvorschlag:
    def test_vorschlag_bis_zielbestand(self, admin_client, articles):
        groups = admin_client.get(f"{BASE}/suggestions").json()
        by_nr = {i["article_number"]: (g, i) for g in groups for i in g["items"]}
        assert "FIL-001" not in by_nr  # Bestand reicht
        g, zk = by_nr["ZK-001"]
        assert g["supplier_name"] == "Quad Teile GmbH"
        assert zk["suggested_quantity"] == 9  # Ziel 10 − Bestand 1
        assert zk["supplier_article_number"] == "NGK-CR7"
        assert Decimal(zk["unit_price"]) == Decimal("4.50")

    def test_ohne_zielbestand_bis_mindestbestand_und_ohne_lieferant_zuletzt(self, admin_client, articles):
        groups = admin_client.get(f"{BASE}/suggestions").json()
        assert groups[-1]["supplier_id"] is None
        assert groups[-1]["supplier_name"] == "Ohne Lieferant"
        oel = groups[-1]["items"][0]
        assert oel["article_number"] == "OEL-001" and oel["suggested_quantity"] == 4

    def test_offene_bestellung_wird_beruecksichtigt(self, admin_client, order, articles):
        groups = admin_client.get(f"{BASE}/suggestions").json()
        nrs = [i["article_number"] for g in groups for i in g["items"]]
        assert "ZK-001" not in nrs  # 1 + 9 bestellt = 10 ≥ Mindestbestand

    def test_teilbestellung_ergibt_restvorschlag(self, admin_client, supplier, articles):
        admin_client.post(BASE, json=_order_payload(supplier, articles[0], qty=1))
        groups = admin_client.get(f"{BASE}/suggestions").json()
        zk = next(i for g in groups for i in g["items"] if i["article_number"] == "ZK-001")
        assert zk["on_order_quantity"] == 1 and zk["suggested_quantity"] == 8

    def test_reservierung_erhoeht_bedarf(self, admin_client, db, articles, sample_customer):
        from app.models.stock_reservation import StockReservation

        a3 = articles[2]
        db.add(StockReservation(article_id=a3.id, quantity=4, status="active"))
        db.flush()
        groups = admin_client.get(f"{BASE}/suggestions").json()
        fil = next(i for g in groups for i in g["items"] if i["article_number"] == "FIL-001")
        assert fil["reserved_quantity"] == 4
        assert fil["suggested_quantity"] == 5  # Ziel 6 − (5 − 4)

    def test_inaktive_artikel_ignoriert(self, admin_client, db, articles):
        articles[1].is_active = False
        db.flush()
        nrs = [i["article_number"] for g in admin_client.get(f"{BASE}/suggestions").json() for i in g["items"]]
        assert "OEL-001" not in nrs


class TestBestellung:
    def test_anlegen_summen_und_nummer(self, order, articles):
        assert order["order_number"].startswith("BE-") and order["order_number"].endswith("-0001")
        assert order["status"] == "draft"
        assert order["supplier_name"] == "Quad Teile GmbH"
        # 9 × 4,50 = 40,50 + 5,95 = 46,45 netto; MwSt 8,83; brutto 55,28
        assert Decimal(order["net_amount"]) == Decimal("46.45")
        assert Decimal(order["vat_amount"]) == Decimal("8.83")
        assert Decimal(order["gross_amount"]) == Decimal("55.28")
        pos1 = order["items"][0]
        assert pos1["supplier_article_number"] == "NGK-CR7"  # aus dem Artikel übernommen
        assert pos1["article_number"] == "ZK-001"

    def test_fortlaufende_nummer(self, admin_client, order, supplier, articles):
        second = admin_client.post(BASE, json=_order_payload(supplier, articles[0])).json()
        assert second["order_number"].endswith("-0002")

    @pytest.mark.parametrize("change,msg", [
        ({"items": []}, None),
        ({"expected_date": "2026-10-01"}, "Liefertermin"),
    ])
    def test_ungueltige_eingaben(self, admin_client, supplier, articles, change, msg):
        body = {**_order_payload(supplier, articles[0]), **change}
        res = admin_client.post(BASE, json=body)
        assert res.status_code == 422
        if msg:
            assert msg in res.text

    def test_menge_muss_ganzzahlig_positiv(self, admin_client, supplier, articles):
        body = _order_payload(supplier, articles[0], qty=0)
        assert admin_client.post(BASE, json=body).status_code == 422

    def test_unbekannter_lieferant(self, admin_client, supplier, articles):
        body = {**_order_payload(supplier, articles[0]), "supplier_id": "00000000-0000-0000-0000-000000000000"}
        assert admin_client.post(BASE, json=body).status_code == 400

    def test_entwurf_bearbeiten_und_loeschen(self, admin_client, order, supplier, articles):
        res = admin_client.put(f"{BASE}/{order['id']}", json=_order_payload(supplier, articles[0], qty=2))
        assert res.status_code == 200 and Decimal(res.json()["net_amount"]) == Decimal("14.95")
        assert admin_client.delete(f"{BASE}/{order['id']}").status_code == 204
        assert admin_client.get(f"{BASE}/{order['id']}").status_code == 404

    def test_bestellt_nicht_mehr_aenderbar(self, admin_client, order, supplier, articles):
        admin_client.post(f"{BASE}/{order['id']}/mark-sent")
        assert admin_client.put(f"{BASE}/{order['id']}", json=_order_payload(supplier, articles[0])).status_code == 400
        assert admin_client.delete(f"{BASE}/{order['id']}").status_code == 400

    def test_liste_filter(self, admin_client, order):
        assert len(admin_client.get(f"{BASE}?open_only=true").json()) == 1
        assert admin_client.get(f"{BASE}?status_filter=received").json() == []

    def test_audit(self, admin_client, db, order):
        from app.models.audit_log import AuditLog

        assert db.query(AuditLog).filter(AuditLog.entity_type == "purchase_order", AuditLog.action == "create").count() == 1


class TestVersand:
    def test_pdf(self, admin_client, order, company_settings):
        from io import BytesIO

        from pypdf import PdfReader

        res = admin_client.get(f"{BASE}/{order['id']}/pdf")
        assert res.status_code == 200 and res.headers["content-type"] == "application/pdf"
        text = "".join(p.extract_text() for p in PdfReader(BytesIO(res.content)).pages)
        for expected in ("Bestellung", order["order_number"], "Quad Teile GmbH", "K-4711", "NGK-CR7", "ZK-001",
                         "46,45", "55,28", "20.10.2026"):
            assert expected in text, expected

    def test_mail_setzt_bestellt(self, admin_client, order, monkeypatch):
        sent = {}

        def fake_send(db, **kwargs):
            sent.update(kwargs)

        monkeypatch.setattr("app.services.email.send_email_with_attachment", fake_send)
        res = admin_client.post(f"{BASE}/{order['id']}/send-email", json={})
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "sent"
        assert res.json()["sent_to_email"] == "bestellung@quadteile.de"
        assert sent["to_email"] == "bestellung@quadteile.de"
        assert "K-4711" in sent["body"] and sent["attachment_data"].startswith(b"%PDF")

    def test_mail_ohne_adresse(self, admin_client, db, order, supplier):
        supplier.email = None
        db.flush()
        res = admin_client.post(f"{BASE}/{order['id']}/send-email", json={})
        assert res.status_code == 400 and "E-Mail-Adresse" in res.json()["detail"]

    def test_mailfehler_status_bleibt(self, admin_client, order, monkeypatch):
        def boom(db, **kwargs):
            raise RuntimeError("SMTP nicht erreichbar")

        monkeypatch.setattr("app.services.email.send_email_with_attachment", boom)
        assert admin_client.post(f"{BASE}/{order['id']}/send-email", json={}).status_code == 500
        assert admin_client.get(f"{BASE}/{order['id']}").json()["status"] == "draft"

    def test_bestellen_nur_admin(self, client, werkstatt_user, admin_user, order):
        from app.core.security import create_access_token

        client.headers["Authorization"] = f"Bearer {create_access_token(str(werkstatt_user.id))}"
        assert client.post(f"{BASE}/{order['id']}/mark-sent").status_code == 403
        assert client.post(f"{BASE}/{order['id']}/send-email", json={}).status_code == 403
        assert client.get(f"{BASE}/{order['id']}").status_code == 200  # ansehen darf jeder


class TestWareneingang:
    @pytest.fixture()
    def sent(self, admin_client, order):
        res = admin_client.post(f"{BASE}/{order['id']}/mark-sent")
        assert res.json()["status"] == "sent"
        return res.json()

    def _lines(self, order, *qtys):
        return [{"item_id": it["id"], "quantity": q} for it, q in zip(order["items"], qtys)]

    def test_entwurf_kein_wareneingang(self, admin_client, order):
        res = admin_client.post(f"{BASE}/{order['id']}/receive", json={"lines": self._lines(order, 9, 1)})
        assert res.status_code == 400 and "Entwurf" in res.json()["detail"]

    def test_teillieferung_und_rest(self, admin_client, db, sent, articles):
        from app.models.stock_movement import StockMovement

        a1 = articles[0]
        res = admin_client.post(f"{BASE}/{sent['id']}/receive",
                                json={"lines": self._lines(sent, 4, 0), "delivery_note": "LS-100"})
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "partial"
        db.refresh(a1)
        assert a1.stock_quantity == 5
        mv = db.query(StockMovement).filter(StockMovement.reference_id == sent["id"]).one()
        assert mv.movement_type == "incoming" and mv.quantity == 4 and "LS-100" in mv.notes

        res = admin_client.post(f"{BASE}/{sent['id']}/receive", json={"lines": self._lines(sent, 5, 1)})
        assert res.json()["status"] == "received"
        db.refresh(a1)
        assert a1.stock_quantity == 10
        # Freie Position (Versandkosten) bucht nichts ins Lager
        assert db.query(StockMovement).filter(StockMovement.reference_id == sent["id"]).count() == 2

    def test_mehr_als_offen_abgelehnt(self, admin_client, db, sent, articles):
        res = admin_client.post(f"{BASE}/{sent['id']}/receive", json={"lines": self._lines(sent, 10, 0)})
        assert res.status_code == 400 and "nur noch 9 offen" in res.json()["detail"]
        db.refresh(articles[0])
        assert articles[0].stock_quantity == 1  # nichts gebucht

    def test_null_mengen_abgelehnt(self, admin_client, sent):
        res = admin_client.post(f"{BASE}/{sent['id']}/receive", json={"lines": self._lines(sent, 0, 0)})
        assert res.status_code == 400

    def test_fremde_position_abgelehnt(self, admin_client, sent):
        res = admin_client.post(f"{BASE}/{sent['id']}/receive",
                                json={"lines": [{"item_id": "00000000-0000-0000-0000-000000000000", "quantity": 1}]})
        assert res.status_code == 400

    def test_ek_preis_aktualisieren(self, admin_client, db, supplier, articles):
        a1 = articles[0]
        o = admin_client.post(BASE, json=_order_payload(supplier, a1, qty=2, price="4.80")).json()
        admin_client.post(f"{BASE}/{o['id']}/mark-sent")
        admin_client.post(f"{BASE}/{o['id']}/receive",
                          json={"lines": self._lines(o, 2, 1), "update_purchase_price": True})
        db.refresh(a1)
        assert a1.purchase_price == Decimal("4.80")

    def test_werkstatt_darf_wareneingang(self, client, werkstatt_user, admin_user, sent):
        from app.core.security import create_access_token

        client.headers["Authorization"] = f"Bearer {create_access_token(str(werkstatt_user.id))}"
        res = client.post(f"{BASE}/{sent['id']}/receive", json={"lines": self._lines(sent, 9, 1)})
        assert res.status_code == 200 and res.json()["status"] == "received"

    def test_nach_lieferung_kein_vorschlag_mehr(self, admin_client, sent):
        admin_client.post(f"{BASE}/{sent['id']}/receive", json={"lines": self._lines(sent, 9, 1)})
        nrs = [i["article_number"] for g in admin_client.get(f"{BASE}/suggestions").json() for i in g["items"]]
        assert "ZK-001" not in nrs

    def test_storno_ohne_lieferung(self, admin_client, sent):
        res = admin_client.post(f"{BASE}/{sent['id']}/cancel")
        assert res.json()["status"] == "cancelled"
        assert admin_client.post(f"{BASE}/{sent['id']}/receive", json={"lines": self._lines(sent, 1, 0)}).status_code == 400

    def test_storno_nach_teillieferung_schliesst(self, admin_client, sent):
        admin_client.post(f"{BASE}/{sent['id']}/receive", json={"lines": self._lines(sent, 3, 0)})
        assert admin_client.post(f"{BASE}/{sent['id']}/cancel").json()["status"] == "closed"
        # Rest zählt nicht mehr als „bestellt“ → Artikel erscheint wieder im Vorschlag (Bestand 4 ≥ 3? nein: Ziel)
        groups = admin_client.get(f"{BASE}/suggestions").json()
        nrs = [i["article_number"] for g in groups for i in g["items"]]
        assert "ZK-001" not in nrs  # Bestand 4 ≥ Mindestbestand 3

    def test_entwurf_nicht_stornierbar(self, admin_client, order):
        assert admin_client.post(f"{BASE}/{order['id']}/cancel").status_code == 400


class TestStammdatenFelder:
    def test_artikel_zielbestand_und_lieferantennr(self, admin_client):
        res = admin_client.post(f"{V1}/articles", json={
            "article_number": "NEU-1", "name": "Neu", "minimum_stock": 2, "target_stock": 8,
            "supplier_article_number": " ABC-9 ",
        })
        assert res.status_code == 201, res.text
        assert res.json()["target_stock"] == 8 and res.json()["supplier_article_number"] == "ABC-9"
        res = admin_client.patch(f"{V1}/articles/{res.json()['id']}", json={"target_stock": 12})
        assert res.json()["target_stock"] == 12

    def test_lieferant_kundennummer(self, admin_client):
        res = admin_client.post(f"{V1}/suppliers", json={"name": "X GmbH", "customer_number": "KD-1"})
        assert res.json()["customer_number"] == "KD-1"
