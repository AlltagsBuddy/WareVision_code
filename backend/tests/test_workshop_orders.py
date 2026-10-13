"""Tests: Werkstattaufträge."""

from datetime import date


class TestWerkstattauftragCRUD:
    def test_auftrag_erstellen(self, admin_client, sample_customer, sample_vehicle):
        """Neuen Werkstattauftrag anlegen."""
        res = admin_client.post("/api/v1/workshop-orders/", json={
            "customer_id": str(sample_customer.id),
            "vehicle_id": str(sample_vehicle.id),
            "complaint_description": "Bremsen quietschen",
        })
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "new"
        assert data["order_number"].startswith("WO-")
        assert data["complaint_description"] == "Bremsen quietschen"

    def test_auftrag_liste(self, admin_client, db, sample_customer, sample_vehicle, admin_user):
        """Auftrags-Liste abrufen."""
        from app.models.workshop_order import WorkshopOrder
        order = WorkshopOrder(
            customer_id=sample_customer.id,
            vehicle_id=sample_vehicle.id,
            order_number="WO-LIST-0001",
            status="new",
            created_by=admin_user.id,
        )
        db.add(order)
        db.flush()

        res = admin_client.get("/api/v1/workshop-orders/")
        assert res.status_code == 200
        assert len(res.json()) >= 1

    def test_status_aktualisieren(self, admin_client, db, sample_customer, sample_vehicle, admin_user):
        """Status von 'new' auf 'in_progress' ändern."""
        from app.models.workshop_order import WorkshopOrder
        order = WorkshopOrder(
            customer_id=sample_customer.id,
            vehicle_id=sample_vehicle.id,
            order_number="WO-STATUS-0001",
            status="new",
            created_by=admin_user.id,
        )
        db.add(order)
        db.flush()

        res = admin_client.patch(f"/api/v1/workshop-orders/{order.id}", json={
            "status": "in_progress",
        })
        assert res.status_code == 200
        assert res.json()["status"] == "in_progress"

    def test_ungültiger_status_verboten(self, admin_client, db, sample_customer, sample_vehicle, admin_user):
        """Ungültiger Status → 422."""
        from app.models.workshop_order import WorkshopOrder
        order = WorkshopOrder(
            customer_id=sample_customer.id,
            vehicle_id=sample_vehicle.id,
            order_number="WO-INVALID-0001",
            status="new",
            created_by=admin_user.id,
        )
        db.add(order)
        db.flush()

        res = admin_client.patch(f"/api/v1/workshop-orders/{order.id}", json={
            "status": "ungültig",
        })
        assert res.status_code == 422

    def test_werkstatt_benutzer_kann_auftrag_sehen(self, werkstatt_client, db, sample_customer, sample_vehicle, admin_user):
        """Werkstatt-Benutzer hat Lesezugriff."""
        from app.models.workshop_order import WorkshopOrder
        order = WorkshopOrder(
            customer_id=sample_customer.id,
            vehicle_id=sample_vehicle.id,
            order_number="WO-PERM-0001",
            status="new",
            created_by=admin_user.id,
        )
        db.add(order)
        db.flush()

        res = werkstatt_client.get("/api/v1/workshop-orders/")
        assert res.status_code == 200


class TestWerkstattauftragValidierung:
    def test_negativer_preis_verboten(self, admin_client, db, sample_customer, sample_vehicle, admin_user):
        """Negative Arbeitsstunden/Preise → 422."""
        from app.models.workshop_order import WorkshopOrder
        order = WorkshopOrder(
            customer_id=sample_customer.id,
            vehicle_id=sample_vehicle.id,
            order_number="WO-NEG-0001",
            status="new",
            created_by=admin_user.id,
        )
        db.add(order)
        db.flush()

        res = admin_client.post(f"/api/v1/workshop-orders/{order.id}/items", json={
            "description": "Ungültige Position",
            "quantity": -1,
            "unit_price": 100.00,
        })
        assert res.status_code == 422
