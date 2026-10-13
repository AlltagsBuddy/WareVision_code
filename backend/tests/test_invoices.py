"""Tests: Rechnungen, Mahnwesen, PDF-Download."""

from datetime import date, timedelta
from decimal import Decimal

import pytest


class TestRechnungenCRUD:
    def test_rechnung_erstellen(self, admin_client, sample_customer):
        """Rechnung mit manuellen Positionen erstellen."""
        res = admin_client.post("/api/v1/invoices/", json={
            "customer_id": str(sample_customer.id),
            "invoice_date": str(date.today()),
            "items": [
                {"description": "Reparatur", "quantity": 1, "unit_price": 120.00, "vat_rate": 19},
            ],
        })
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "draft"
        assert data["customer_id"] == str(sample_customer.id)
        assert data["invoice_number"].startswith("RE-")

    def test_rechnung_leere_positionen_verboten(self, admin_client, sample_customer):
        """Rechnung ohne Positionen ist ungültig (422)."""
        res = admin_client.post("/api/v1/invoices/", json={
            "customer_id": str(sample_customer.id),
            "invoice_date": str(date.today()),
            "items": [
                {"description": "", "quantity": 1, "unit_price": 10.00},
            ],
        })
        assert res.status_code == 422

    def test_faelligkeitsdatum_vor_rechnungsdatum(self, admin_client, sample_customer):
        """Fälligkeitsdatum vor Rechnungsdatum → 422."""
        today = date.today()
        res = admin_client.post("/api/v1/invoices/", json={
            "customer_id": str(sample_customer.id),
            "invoice_date": str(today),
            "due_date": str(today - timedelta(days=1)),
            "items": [{"description": "Test", "quantity": 1, "unit_price": 10.00}],
        })
        assert res.status_code == 422

    def test_rechnung_liste(self, admin_client, sample_invoice):
        """Rechnungsliste enthält die angelegte Rechnung."""
        res = admin_client.get("/api/v1/invoices/")
        assert res.status_code == 200
        ids = [i["id"] for i in res.json()]
        assert str(sample_invoice.id) in ids

    def test_filter_ueberfaellig(self, admin_client, sample_invoice):
        """Überfälligkeitsfilter findet abgelaufene Rechnungen."""
        res = admin_client.get("/api/v1/invoices/?overdue=true")
        assert res.status_code == 200
        # sample_invoice hat due_date in der Vergangenheit → muss in der Liste sein
        ids = [i["id"] for i in res.json()]
        assert str(sample_invoice.id) in ids


class TestRechnungsAktionen:
    def test_rechnung_ausstellen(self, admin_client, db, sample_customer, admin_user):
        """Entwurf → ausgestellt."""
        from app.models.invoice import Invoice
        from app.models.customer import Customer

        inv = Invoice(
            customer_id=sample_customer.id,
            invoice_number="RE-ACT-0001",
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=14),
            status="draft",
            currency="EUR",
            net_amount=Decimal("100.00"),
            vat_amount=Decimal("19.00"),
            gross_amount=Decimal("119.00"),
            created_by=admin_user.id,
        )
        db.add(inv)
        db.flush()

        res = admin_client.post(f"/api/v1/invoices/{inv.id}/issue")
        assert res.status_code == 200
        assert res.json()["status"] == "issued"

    def test_entwurf_kann_nicht_zweimal_ausgestellt_werden(self, admin_client, sample_invoice):
        """Ausgestellte Rechnung erneut ausstellen → 400."""
        res = admin_client.post(f"/api/v1/invoices/{sample_invoice.id}/issue")
        assert res.status_code == 400

    def test_als_bezahlt_markieren(self, admin_client, sample_invoice):
        """Rechnung als bezahlt markieren."""
        res = admin_client.post(f"/api/v1/invoices/{sample_invoice.id}/mark-paid")
        assert res.status_code == 200
        assert res.json()["status"] == "paid"

    def test_stornierung(self, admin_client, sample_invoice):
        """Rechnung stornieren erzeugt eine Stornorechnung."""
        res = admin_client.post(f"/api/v1/invoices/{sample_invoice.id}/cancel", json={"reason": "Test"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "cancelled"
        assert data["cancellation_invoice_id"] is not None

    def test_stornierung_bereits_stornierter_rechnung(self, admin_client, sample_invoice):
        """Stornierte Rechnung kann nicht nochmals storniert werden."""
        admin_client.post(f"/api/v1/invoices/{sample_invoice.id}/cancel")
        res = admin_client.post(f"/api/v1/invoices/{sample_invoice.id}/cancel")
        assert res.status_code == 400


class TestMahnwesen:
    def test_mahnstufe_setzen(self, admin_client, sample_invoice):
        """Mahnstufe 1 auf überfällige Rechnung setzen."""
        res = admin_client.post(f"/api/v1/invoices/{sample_invoice.id}/reminder?reminder_level=1")
        assert res.status_code == 200
        data = res.json()
        assert data["reminder_level"] == 1
        assert data["reminder_date"] is not None

    def test_mahnstufe_eskalieren(self, admin_client, sample_invoice):
        """Mahnstufe 1 → 2 → 3."""
        admin_client.post(f"/api/v1/invoices/{sample_invoice.id}/reminder?reminder_level=1")
        admin_client.post(f"/api/v1/invoices/{sample_invoice.id}/reminder?reminder_level=2")
        res = admin_client.post(f"/api/v1/invoices/{sample_invoice.id}/reminder?reminder_level=3")
        assert res.status_code == 200
        assert res.json()["reminder_level"] == 3

    def test_mahnstufe_4_ungueltig(self, admin_client, sample_invoice):
        """Mahnstufe > 3 → 422 (Validierungsfehler)."""
        res = admin_client.post(f"/api/v1/invoices/{sample_invoice.id}/reminder?reminder_level=4")
        assert res.status_code == 422

    def test_mahnung_bezahlte_rechnung_verboten(self, admin_client, db, sample_invoice):
        """Bezahlte Rechnung kann nicht gemahnt werden."""
        sample_invoice.status = "paid"
        db.flush()
        res = admin_client.post(f"/api/v1/invoices/{sample_invoice.id}/reminder?reminder_level=1")
        assert res.status_code == 400

    def test_mahnbrief_pdf_download(self, admin_client, db, sample_invoice):
        """Mahnbrief-PDF kann nach Setzen der Mahnstufe heruntergeladen werden."""
        # Zuerst Mahnstufe setzen
        admin_client.post(f"/api/v1/invoices/{sample_invoice.id}/reminder?reminder_level=1")

        res = admin_client.get(f"/api/v1/invoices/{sample_invoice.id}/reminder-pdf")
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert len(res.content) > 1000  # PDF hat Mindestgröße

    def test_mahnbrief_ohne_mahnstufe_verboten(self, admin_client, sample_invoice):
        """Mahnbrief ohne Mahnstufe → 400."""
        res = admin_client.get(f"/api/v1/invoices/{sample_invoice.id}/reminder-pdf")
        assert res.status_code == 400

    def test_rechnungs_pdf_download(self, admin_client, sample_invoice):
        """Rechnungs-PDF herunterladen."""
        res = admin_client.get(f"/api/v1/invoices/{sample_invoice.id}/pdf")
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert len(res.content) > 500
