"""Tests: Wartungspläne."""


class TestWartungsplanCRUD:
    def test_plan_erstellen(self, admin_client, sample_manufacturer):
        """Wartungsplan anlegen."""
        res = admin_client.post("/api/v1/maintenance-plans", json={
            "manufacturer_id": str(sample_manufacturer.id),
            "name": "1000-km-Inspektion",
            "interval_km": 1000,
            "interval_months": 12,
        })
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "1000-km-Inspektion"
        assert data["interval_km"] == 1000
        assert data["interval_months"] == 12

    def test_plan_liste(self, admin_client, db, sample_manufacturer):
        """Wartungsplan-Liste abrufen."""
        from app.models.maintenance_plan import MaintenancePlan
        plan = MaintenancePlan(
            manufacturer_id=sample_manufacturer.id,
            name="Testplan-Liste",
        )
        db.add(plan)
        db.flush()

        res = admin_client.get("/api/v1/maintenance-plans")
        assert res.status_code == 200
        names = [p["name"] for p in res.json()]
        assert "Testplan-Liste" in names

    def test_plan_abrufen(self, admin_client, db, sample_manufacturer):
        """Einzelnen Wartungsplan abrufen."""
        from app.models.maintenance_plan import MaintenancePlan
        plan = MaintenancePlan(
            manufacturer_id=sample_manufacturer.id,
            name="Testplan-Get",
        )
        db.add(plan)
        db.flush()

        res = admin_client.get(f"/api/v1/maintenance-plans/{plan.id}")
        assert res.status_code == 200
        assert res.json()["id"] == str(plan.id)

    def test_plan_aktualisieren(self, admin_client, db, sample_manufacturer):
        """Wartungsplan Name und Intervall ändern."""
        from app.models.maintenance_plan import MaintenancePlan
        plan = MaintenancePlan(
            manufacturer_id=sample_manufacturer.id,
            name="Alt",
        )
        db.add(plan)
        db.flush()

        res = admin_client.patch(f"/api/v1/maintenance-plans/{plan.id}", json={
            "name": "Neu",
            "interval_hours": 50,
        })
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "Neu"
        assert data["interval_hours"] == 50

    def test_plan_loeschen(self, admin_client, db, sample_manufacturer):
        """Wartungsplan löschen."""
        from app.models.maintenance_plan import MaintenancePlan
        plan = MaintenancePlan(
            manufacturer_id=sample_manufacturer.id,
            name="Zu löschen",
        )
        db.add(plan)
        db.flush()

        res = admin_client.delete(f"/api/v1/maintenance-plans/{plan.id}")
        assert res.status_code == 204

        res = admin_client.get(f"/api/v1/maintenance-plans/{plan.id}")
        assert res.status_code == 404

    def test_plan_fuer_fahrzeug(self, admin_client, db, sample_vehicle, sample_manufacturer):
        """Plan per Fahrzeug abrufen (Treffer über Hersteller-Fallback)."""
        from app.models.maintenance_plan import MaintenancePlan
        # Hersteller-Fallback: kein vehicle_model_id → passt zu allen Fahrzeugen des Herstellers
        plan = MaintenancePlan(
            manufacturer_id=sample_manufacturer.id,
            name="Fahrzeugplan",
            vehicle_model_id=None,
        )
        db.add(plan)
        db.flush()

        res = admin_client.get(f"/api/v1/maintenance-plans/for-vehicle/{sample_vehicle.id}")
        assert res.status_code == 200
        assert res.json()["id"] == str(plan.id)

    def test_aufgabe_hinzufuegen(self, admin_client, db, sample_manufacturer):
        """Aufgabe zu Wartungsplan hinzufügen."""
        from app.models.maintenance_plan import MaintenancePlan
        plan = MaintenancePlan(
            manufacturer_id=sample_manufacturer.id,
            name="Plan mit Aufgaben",
        )
        db.add(plan)
        db.flush()

        res = admin_client.post(f"/api/v1/maintenance-plans/{plan.id}/tasks", json={
            "name": "Ölwechsel",
            "description": "Motoröl und Filter wechseln",
            "sort_order": 1,
        })
        assert res.status_code == 201
        assert res.json()["name"] == "Ölwechsel"

    def test_aufgaben_liste(self, admin_client, db, sample_manufacturer):
        """Aufgabenliste eines Plans abrufen."""
        from app.models.maintenance_plan import MaintenancePlan, MaintenanceTask
        plan = MaintenancePlan(
            manufacturer_id=sample_manufacturer.id,
            name="Plan Aufgabenliste",
        )
        db.add(plan)
        db.flush()
        task = MaintenanceTask(maintenance_plan_id=plan.id, name="Luftfilter", sort_order=0)
        db.add(task)
        db.flush()

        res = admin_client.get(f"/api/v1/maintenance-plans/{plan.id}/tasks")
        assert res.status_code == 200
        assert any(t["name"] == "Luftfilter" for t in res.json())
