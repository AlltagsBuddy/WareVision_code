"""Tests: Fahrzeugverwaltung."""

from uuid import UUID


class TestFahrzeugCRUD:
    def test_fahrzeug_erstellen(self, admin_client, sample_customer, sample_manufacturer):
        """Neues Fahrzeug anlegen."""
        res = admin_client.post("/api/v1/vehicles", json={
            "customer_id": str(sample_customer.id),
            "manufacturer_id": str(sample_manufacturer.id),
            "category": "quad",
            "model_name_free": "Testmodell 450",
        })
        assert res.status_code == 201
        data = res.json()
        assert data["category"] == "quad"
        assert data["customer_id"] == str(sample_customer.id)
        assert data["is_active"] is True

    def test_fahrzeug_mit_vin(self, admin_client, sample_customer, sample_manufacturer):
        """Fahrzeug mit VIN und Kennzeichen anlegen."""
        res = admin_client.post("/api/v1/vehicles", json={
            "customer_id": str(sample_customer.id),
            "manufacturer_id": str(sample_manufacturer.id),
            "category": "motorcycle",
            "vin": "WV1ZZZ1JZXW000001",
            "license_plate": "NU-AB 123",
        })
        assert res.status_code == 201
        data = res.json()
        assert data["vin"] == "WV1ZZZ1JZXW000001"
        assert data["license_plate"] == "NU-AB 123"

    def test_fahrzeug_liste(self, admin_client, sample_vehicle):
        """Fahrzeugliste abrufen."""
        res = admin_client.get("/api/v1/vehicles")
        assert res.status_code == 200
        ids = [v["id"] for v in res.json()]
        assert str(sample_vehicle.id) in ids

    def test_fahrzeug_nach_kunde_filtern(self, admin_client, sample_vehicle, sample_customer):
        """Fahrzeuge nach Kunden filtern."""
        res = admin_client.get(f"/api/v1/vehicles?customer_id={sample_customer.id}")
        assert res.status_code == 200
        assert all(v["customer_id"] == str(sample_customer.id) for v in res.json())

    def test_fahrzeug_abrufen(self, admin_client, sample_vehicle):
        """Einzelnes Fahrzeug abrufen."""
        res = admin_client.get(f"/api/v1/vehicles/{sample_vehicle.id}")
        assert res.status_code == 200
        assert res.json()["id"] == str(sample_vehicle.id)

    def test_fahrzeug_aktualisieren(self, admin_client, sample_vehicle):
        """Fahrzeug aktualisieren."""
        res = admin_client.patch(f"/api/v1/vehicles/{sample_vehicle.id}", json={
            "license_plate": "NU-XY 999",
            "mileage": 12500,
        })
        assert res.status_code == 200
        data = res.json()
        assert data["license_plate"] == "NU-XY 999"
        assert data["mileage"] == 12500

    def test_fahrzeug_deaktivieren(self, admin_client, sample_vehicle):
        """Fahrzeug deaktivieren (Soft-Delete)."""
        res = admin_client.delete(f"/api/v1/vehicles/{sample_vehicle.id}")
        assert res.status_code == 204

        # Standardabfrage zeigt deaktiviertes Fahrzeug nicht
        res = admin_client.get("/api/v1/vehicles")
        ids = [v["id"] for v in res.json()]
        assert str(sample_vehicle.id) not in ids

        # Mit include_inactive=true wieder sichtbar
        res = admin_client.get("/api/v1/vehicles?include_inactive=true")
        ids = [v["id"] for v in res.json()]
        assert str(sample_vehicle.id) in ids

    def test_unbekanntes_fahrzeug_404(self, admin_client):
        """Unbekannte UUID → 404."""
        res = admin_client.get("/api/v1/vehicles/00000000-0000-0000-0000-000000000000")
        assert res.status_code == 404

    def test_werkstatt_benutzer_hat_lesezugriff(self, werkstatt_client, sample_vehicle):
        """Werkstatt-Benutzer darf Fahrzeuge lesen."""
        res = werkstatt_client.get("/api/v1/vehicles")
        assert res.status_code == 200
