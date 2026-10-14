"""Tests: Angebote und Kostenvoranschläge."""

from datetime import date, timedelta

import pytest

BASE = "/api/v1/quotes"


def _payload(customer_id, vehicle_id=None, **over):
    """Standard-Angebot mit Arbeit, Material und 7-%-Position."""
    data = {
        "quote_type": "offer",
        "customer_id": str(customer_id),
        "vehicle_id": str(vehicle_id) if vehicle_id else None,
        "quote_date": "2026-10-13",
        "subject": "Reparatur Bremsanlage",
        "notes": "Termin nach Absprache.",
        "items": [
            {"item_type": "labor", "description": "Arbeitszeit", "quantity": 2.5, "unit": "Std.", "unit_price": 89, "vat_rate": 19},
            {"item_type": "service", "description": "Teil", "quantity": 2, "unit": "Stück", "unit_price": 12.345, "vat_rate": 19},
            {"item_type": "service", "description": "Fachbuch", "quantity": 1, "unit": "Stk", "unit_price": 24.99, "vat_rate": 7},
        ],
    }
    data.update(over)
    return data


@pytest.fixture()
def quote(admin_client, sample_customer, sample_vehicle):
    """Angelegtes Angebot (Entwurf)."""
    res = admin_client.post(BASE, json=_payload(sample_customer.id, sample_vehicle.id))
    assert res.status_code == 201, res.text
    return res.json()


class TestAngebotAnlegen:
    def test_nummer_und_gueltigkeit(self, quote):
        assert quote["quote_number"].startswith(f"AN-{date.today().year}-")
        assert quote["status"] == "draft"
        # Standard-Gültigkeit 30 Tage
        assert quote["valid_until"] == (date(2026, 10, 13) + timedelta(days=30)).isoformat()

    def test_summen_je_steuersatz(self, quote):
        """Preis wird auf Cent gerundet (12,345 → 12,35), MwSt je Satz kaufmännisch gerundet."""
        assert quote["items"][1]["unit_price"] == "12.35"
        assert quote["items"][1]["line_total_net"] == "24.70"
        # 19 %: 222,50 + 24,70 = 247,20 → 46,97; 7 %: 24,99 → 1,75
        assert quote["net_amount"] == "272.19"
        assert quote["vat_amount"] == "48.72"
        assert quote["gross_amount"] == "320.91"

    def test_positionen_nummeriert(self, quote):
        assert [i["position"] for i in quote["items"]] == [1, 2, 3]

    def test_ohne_positionen_abgelehnt(self, admin_client, sample_customer):
        res = admin_client.post(BASE, json=_payload(sample_customer.id, items=[]))
        assert res.status_code == 422

    def test_gueltig_bis_vor_datum_abgelehnt(self, admin_client, sample_customer):
        res = admin_client.post(BASE, json=_payload(sample_customer.id, valid_until="2026-10-01"))
        assert res.status_code == 422

    def test_negativer_preis_abgelehnt(self, admin_client, sample_customer):
        items = [{"item_type": "service", "description": "x", "quantity": 1, "unit_price": -1, "vat_rate": 19}]
        res = admin_client.post(BASE, json=_payload(sample_customer.id, items=items))
        assert res.status_code == 422

    def test_fremdes_fahrzeug_abgelehnt(self, admin_client, sample_vehicle, b2b_customer):
        res = admin_client.post(BASE, json=_payload(b2b_customer.id, sample_vehicle.id))
        assert res.status_code == 400
        assert "gehört nicht" in res.json()["detail"]

    def test_kostenvoranschlag_ohne_gueltigkeit(self, admin_client, sample_customer):
        res = admin_client.post(BASE, json=_payload(sample_customer.id, quote_type="estimate"))
        assert res.status_code == 201
        assert res.json()["valid_until"] is None

    def test_nummern_fortlaufend(self, admin_client, sample_customer, quote):
        second = admin_client.post(BASE, json=_payload(sample_customer.id)).json()
        n1 = int(quote["quote_number"].split("-")[-1])
        n2 = int(second["quote_number"].split("-")[-1])
        assert n2 == n1 + 1


class TestAngebotBearbeiten:
    def test_entwurf_bearbeiten(self, admin_client, quote, sample_customer):
        data = _payload(sample_customer.id, items=_payload(sample_customer.id)["items"][:1])
        res = admin_client.put(f"{BASE}/{quote['id']}", json=data)
        assert res.status_code == 200
        assert len(res.json()["items"]) == 1
        assert res.json()["gross_amount"] == "264.78"  # 222,50 + 42,28

    def test_versendet_nicht_bearbeitbar(self, admin_client, quote, sample_customer):
        admin_client.post(f"{BASE}/{quote['id']}/status", json={"status": "sent"})
        res = admin_client.put(f"{BASE}/{quote['id']}", json=_payload(sample_customer.id))
        assert res.status_code == 400

    def test_entwurf_loeschbar_versendet_nicht(self, admin_client, quote, sample_customer):
        other = admin_client.post(BASE, json=_payload(sample_customer.id)).json()
        assert admin_client.delete(f"{BASE}/{other['id']}").status_code == 204
        admin_client.post(f"{BASE}/{quote['id']}/status", json={"status": "sent"})
        assert admin_client.delete(f"{BASE}/{quote['id']}").status_code == 400

    def test_neue_version(self, admin_client, quote):
        admin_client.post(f"{BASE}/{quote['id']}/status", json={"status": "sent"})
        res = admin_client.post(f"{BASE}/{quote['id']}/duplicate")
        assert res.status_code == 201
        copy = res.json()
        assert copy["status"] == "draft"
        assert copy["previous_quote_id"] == quote["id"]
        assert copy["quote_number"] != quote["quote_number"]
        assert len(copy["items"]) == 3
        assert copy["gross_amount"] == quote["gross_amount"]


class TestStatus:
    @pytest.mark.parametrize("path,expected", [
        (["sent", "accepted"], 200),
        (["sent", "rejected", "accepted"], 200),
        (["accepted", "sent"], 400),     # zurück auf versendet nicht erlaubt
    ])
    def test_statuswechsel(self, admin_client, quote, path, expected):
        res = None
        for st in path:
            res = admin_client.post(f"{BASE}/{quote['id']}/status", json={"status": st})
        assert res.status_code == expected

    def test_ungueltiger_status(self, admin_client, quote):
        res = admin_client.post(f"{BASE}/{quote['id']}/status", json={"status": "converted"})
        assert res.status_code == 422


class TestUmwandlung:
    def test_in_werkstattauftrag(self, admin_client, db, sample_customer, sample_vehicle, sample_article):
        items = [
            {"item_type": "labor", "description": "Arbeit", "quantity": 1, "unit": "Std.", "unit_price": 89, "vat_rate": 19},
            {"item_type": "material", "article_id": str(sample_article.id), "description": sample_article.name,
             "quantity": 2, "unit": "Stück", "unit_price": 35, "vat_rate": 19},
        ]
        q = admin_client.post(BASE, json=_payload(sample_customer.id, sample_vehicle.id, items=items)).json()
        admin_client.post(f"{BASE}/{q['id']}/status", json={"status": "accepted"})
        res = admin_client.post(f"{BASE}/{q['id']}/convert", json={})
        assert res.status_code == 200, res.text
        converted = res.json()
        assert converted["status"] == "converted"
        order = admin_client.get(f"/api/v1/workshop-orders/{converted['workshop_order_id']}").json()
        assert order["complaint_description"] == "Reparatur Bremsanlage"
        order_items = admin_client.get(f"/api/v1/workshop-orders/{order['id']}/items").json()
        assert len(order_items) == 2
        # Material wurde aus dem Lager gebucht (10 - 2)
        db.refresh(sample_article)
        assert sample_article.stock_quantity == 8

    def test_doppelte_umwandlung_verhindert(self, admin_client, quote):
        assert admin_client.post(f"{BASE}/{quote['id']}/convert", json={}).status_code == 200
        assert admin_client.post(f"{BASE}/{quote['id']}/convert", json={}).status_code == 400

    def test_ohne_fahrzeug(self, admin_client, sample_customer, sample_vehicle):
        q = admin_client.post(BASE, json=_payload(sample_customer.id)).json()
        res = admin_client.post(f"{BASE}/{q['id']}/convert", json={})
        assert res.status_code == 400
        assert "Fahrzeug" in res.json()["detail"]
        res = admin_client.post(f"{BASE}/{q['id']}/convert", json={"vehicle_id": str(sample_vehicle.id)})
        assert res.status_code == 200
        assert res.json()["vehicle_id"] == str(sample_vehicle.id)

    def test_abgelehnt_nicht_umwandelbar(self, admin_client, quote):
        admin_client.post(f"{BASE}/{quote['id']}/status", json={"status": "rejected"})
        assert admin_client.post(f"{BASE}/{quote['id']}/convert", json={}).status_code == 400


class TestPdfUndMail:
    def test_angebot_pdf(self, admin_client, quote):
        res = admin_client.get(f"{BASE}/{quote['id']}/pdf")
        assert res.status_code == 200
        assert res.content[:5] == b"%PDF-"

    def test_kva_pdf_mit_hinweis(self, admin_client, sample_customer):
        from io import BytesIO
        from pypdf import PdfReader

        q = admin_client.post(BASE, json=_payload(sample_customer.id, quote_type="estimate")).json()
        res = admin_client.get(f"{BASE}/{q['id']}/pdf")
        text = "".join(p.extract_text() for p in PdfReader(BytesIO(res.content)).pages)
        assert "Kostenvoranschlag" in text
        assert "649 BGB" in text

    def test_mail_ohne_adresse(self, admin_client, db, sample_customer, quote):
        sample_customer.email = None
        db.flush()
        res = admin_client.post(f"{BASE}/{quote['id']}/send-email", json={})
        assert res.status_code == 400

    def test_mail_setzt_versendet(self, admin_client, quote, monkeypatch):
        sent = {}

        def fake_send(db, **kwargs):
            sent.update(kwargs)

        monkeypatch.setattr("app.services.email.send_email_with_attachment", fake_send)
        res = admin_client.post(f"{BASE}/{quote['id']}/send-email", json={"recipient_email": "kunde@test.de"})
        assert res.status_code == 200
        assert res.json()["status"] == "sent"
        assert sent["to_email"] == "kunde@test.de"
        assert sent["attachment_data"][:5] == b"%PDF-"


class TestBerechtigungUndListe:
    def test_liste_und_filter(self, admin_client, quote):
        assert any(q["id"] == quote["id"] for q in admin_client.get(BASE).json())
        assert admin_client.get(f"{BASE}?status_filter=sent").json() == []

    def test_ohne_login(self, client):
        assert client.get(BASE).status_code == 401

    def test_unbekannt(self, admin_client):
        assert admin_client.get(f"{BASE}/00000000-0000-0000-0000-000000000000").status_code == 404
