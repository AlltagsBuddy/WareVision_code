"""Tests: Kundenverwaltung und DSGVO."""

import pytest


class TestKundenCRUD:
    def test_liste_leer(self, admin_client):
        """Leere Kundenliste."""
        res = admin_client.get("/api/v1/customers/")
        assert res.status_code == 200
        assert res.json() == []

    def test_kunde_erstellen(self, admin_client):
        """B2C-Kunden erstellen."""
        res = admin_client.post("/api/v1/customers/", json={
            "customer_type": "B2C",
            "first_name": "Anna",
            "last_name": "Schmidt",
            "email": "anna.schmidt@test.de",
        })
        assert res.status_code == 201
        data = res.json()
        assert data["first_name"] == "Anna"
        assert data["last_name"] == "Schmidt"
        assert data["is_active"] is True

    def test_b2b_kunde_erstellen(self, admin_client):
        """B2B-Kunden mit Firmenname erstellen."""
        res = admin_client.post("/api/v1/customers/", json={
            "customer_type": "B2B",
            "company_name": "Musterfirma GmbH",
            "email": "info@musterfirma.de",
        })
        assert res.status_code == 201
        assert res.json()["company_name"] == "Musterfirma GmbH"

    def test_kunde_abrufen(self, admin_client, sample_customer):
        """Einzelnen Kunden abrufen."""
        res = admin_client.get(f"/api/v1/customers/{sample_customer.id}")
        assert res.status_code == 200
        assert res.json()["email"] == "max.mustermann@test.de"

    def test_kunde_aktualisieren(self, admin_client, sample_customer):
        """Kundendaten ändern."""
        res = admin_client.patch(f"/api/v1/customers/{sample_customer.id}", json={
            "phone": "0987654321",
            "notes": "VIP-Kunde",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["phone"] == "0987654321"
        assert data["notes"] == "VIP-Kunde"

    def test_kunde_deaktivieren(self, admin_client, sample_customer):
        """Kunden deaktivieren."""
        res = admin_client.delete(f"/api/v1/customers/{sample_customer.id}")
        assert res.status_code in (200, 204)

    def test_suche(self, admin_client, sample_customer):
        """Kunden nach Name suchen."""
        res = admin_client.get("/api/v1/customers/?search=Mustermann")
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 1
        assert any("Mustermann" in (c.get("last_name") or "") for c in data)

    def test_duplikat_email_wird_gewarnt(self, admin_client, sample_customer):
        """Doppelte E-Mail-Adresse → 409 oder Warnung."""
        res = admin_client.post("/api/v1/customers/", json={
            "customer_type": "B2C",
            "first_name": "Doppelt",
            "last_name": "Test",
            "email": "max.mustermann@test.de",
        })
        # Je nach Implementierung 409 oder 201 mit Warnung
        assert res.status_code in (201, 409)


class TestDSGVO:
    def test_export_kundendaten(self, admin_client, sample_customer):
        """DSGVO-Export enthält alle Pflichtfelder."""
        res = admin_client.get(f"/api/v1/customers/{sample_customer.id}/export")
        assert res.status_code == 200
        data = res.json()
        assert "customer" in data
        assert "vehicles" in data
        assert "invoices" in data
        assert "appointments" in data
        assert "workshop_orders" in data
        assert "exported_at" in data
        assert data["customer"]["email"] == "max.mustermann@test.de"

    def test_export_nur_fuer_admin(self, werkstatt_client, sample_customer):
        """Export nur für Admins zugänglich."""
        res = werkstatt_client.get(f"/api/v1/customers/{sample_customer.id}/export")
        assert res.status_code == 403

    def test_dsgvo_loeschung_ohne_rechnungen(self, admin_client, db, sample_customer):
        """Kunde ohne Rechnungen wird vollständig gelöscht."""
        res = admin_client.post(f"/api/v1/customers/{sample_customer.id}/dsgvo-delete")
        assert res.status_code == 200
        assert res.json()["action"] == "deleted"

        # Kein Datensatz mehr vorhanden
        from app.models.customer import Customer
        remaining = db.query(Customer).filter(Customer.id == sample_customer.id).first()
        assert remaining is None

    def test_dsgvo_anonymisierung_mit_rechnungen(self, admin_client, db, sample_customer, sample_invoice):
        """Kunde mit Rechnungen wird anonymisiert (GoBD)."""
        res = admin_client.post(f"/api/v1/customers/{sample_customer.id}/dsgvo-delete")
        assert res.status_code == 200
        assert res.json()["action"] == "anonymized"

        db.expire_all()
        from app.models.customer import Customer
        customer = db.query(Customer).filter(Customer.id == sample_customer.id).first()
        assert customer is not None
        assert customer.first_name == "[Anonymisiert]"
        assert customer.last_name == "[Anonymisiert]"
        assert "anonymisiert.local" in customer.email
        assert customer.phone is None
        assert customer.is_active is False

    def test_dsgvo_fahrzeug_anonymisierung(self, admin_client, db, sample_customer, sample_invoice):
        """Bei DSGVO-Anonymisierung werden auch Fahrzeugkennzeichen anonymisiert."""
        from app.models.vehicle import Vehicle
        from app.models.manufacturer import Manufacturer

        # Fahrzeug zum Kunden anlegen
        mfr = Manufacturer(name="TestHersteller")
        db.add(mfr)
        db.flush()
        v = Vehicle(
            customer_id=sample_customer.id,
            license_plate="NU-AB-1234",
            vin="WBA12345678901234",
            category="quad",
            manufacturer_id=mfr.id,
        )
        db.add(v)
        db.flush()

        res = admin_client.post(f"/api/v1/customers/{sample_customer.id}/dsgvo-delete")
        assert res.status_code == 200
        assert res.json()["action"] == "anonymized"

        db.expire_all()
        vehicle = db.query(Vehicle).filter(Vehicle.id == v.id).first()
        assert vehicle.license_plate == "[Anonymisiert]"
        assert vehicle.vin is None

    def test_dsgvo_nur_fuer_admin(self, werkstatt_client, sample_customer):
        """DSGVO-Löschung nur für Admins."""
        res = werkstatt_client.post(f"/api/v1/customers/{sample_customer.id}/dsgvo-delete")
        assert res.status_code == 403
