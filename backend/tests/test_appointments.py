"""Tests: Terminplaner."""

from datetime import datetime, timedelta, timezone


def _dt(offset_hours: int = 0) -> str:
    """ISO-Datetime relativ zu jetzt (UTC)."""
    base = datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc) + timedelta(hours=offset_hours)
    return base.isoformat()


class TestTerminCRUD:
    def test_termin_erstellen(self, admin_client, sample_customer, sample_vehicle):
        """Werkstatttermin anlegen."""
        res = admin_client.post("/api/v1/appointments", json={
            "appointment_type": "workshop",
            "starts_at": _dt(0),
            "ends_at": _dt(2),
            "customer_id": str(sample_customer.id),
            "vehicle_id": str(sample_vehicle.id),
            "title": "Reifenwechsel",
        })
        assert res.status_code == 201
        data = res.json()
        assert data["appointment_type"] == "workshop"
        assert data["title"] == "Reifenwechsel"
        assert data["status"] == "planned"

    def test_termin_ohne_kunden(self, admin_client):
        """Termin ohne Kundenzuordnung ist erlaubt."""
        res = admin_client.post("/api/v1/appointments", json={
            "appointment_type": "test_drive",
            "starts_at": _dt(10),
            "ends_at": _dt(11),
        })
        assert res.status_code == 201

    def test_termin_liste(self, admin_client, db, admin_user, sample_customer):
        """Terminliste abrufen."""
        from app.models.appointment import Appointment
        apt = Appointment(
            appointment_type="workshop",
            starts_at=datetime(2026, 7, 1, 8, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc),
            status="planned",
            customer_id=sample_customer.id,
            created_by=admin_user.id,
        )
        db.add(apt)
        db.flush()

        res = admin_client.get("/api/v1/appointments")
        assert res.status_code == 200
        ids = [a["id"] for a in res.json()]
        assert str(apt.id) in ids

    def test_termin_abrufen(self, admin_client, db, admin_user):
        """Einzelnen Termin abrufen."""
        from app.models.appointment import Appointment
        apt = Appointment(
            appointment_type="test_drive",
            starts_at=datetime(2026, 8, 1, 14, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 8, 1, 15, 0, tzinfo=timezone.utc),
            status="planned",
            created_by=admin_user.id,
        )
        db.add(apt)
        db.flush()

        res = admin_client.get(f"/api/v1/appointments/{apt.id}")
        assert res.status_code == 200
        assert res.json()["id"] == str(apt.id)

    def test_termin_aktualisieren(self, admin_client, db, admin_user):
        """Terminstatus auf 'confirmed' setzen."""
        from app.models.appointment import Appointment
        apt = Appointment(
            appointment_type="workshop",
            starts_at=datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 9, 1, 11, 0, tzinfo=timezone.utc),
            status="planned",
            created_by=admin_user.id,
        )
        db.add(apt)
        db.flush()

        res = admin_client.patch(f"/api/v1/appointments/{apt.id}", json={"status": "confirmed"})
        assert res.status_code == 200
        assert res.json()["status"] == "confirmed"

    def test_termin_stornieren(self, admin_client, db, admin_user):
        """Termin stornieren – Appointment erhält Status 'cancelled'."""
        from app.models.appointment import Appointment
        apt = Appointment(
            appointment_type="workshop",
            starts_at=datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 10, 1, 11, 0, tzinfo=timezone.utc),
            status="planned",
            created_by=admin_user.id,
        )
        db.add(apt)
        db.flush()

        res = admin_client.delete(f"/api/v1/appointments/{apt.id}")
        assert res.status_code == 200

        # Status-Prüfung per GET, da DELETE AppointmentCancelResponse zurückgibt
        detail = admin_client.get(f"/api/v1/appointments/{apt.id}")
        assert detail.status_code == 200
        assert detail.json()["status"] == "cancelled"

    def test_ueberlappung_workshop_termine(self, admin_client):
        """Zwei überlappende Werkstatttermine → 409."""
        admin_client.post("/api/v1/appointments", json={
            "appointment_type": "workshop",
            "starts_at": _dt(20),
            "ends_at": _dt(22),
        })
        res = admin_client.post("/api/v1/appointments", json={
            "appointment_type": "workshop",
            "starts_at": _dt(21),
            "ends_at": _dt(23),
        })
        assert res.status_code == 409

    def test_ueberlappung_probefahrt_erlaubt(self, admin_client):
        """Probefahrten blockieren sich nicht gegenseitig."""
        admin_client.post("/api/v1/appointments", json={
            "appointment_type": "test_drive",
            "starts_at": _dt(30),
            "ends_at": _dt(31),
        })
        res = admin_client.post("/api/v1/appointments", json={
            "appointment_type": "test_drive",
            "starts_at": _dt(30),
            "ends_at": _dt(31),
        })
        assert res.status_code == 201
