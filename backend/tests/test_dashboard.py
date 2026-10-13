"""Tests: Dashboard-Statistiken."""

from datetime import date, timedelta
from decimal import Decimal


class TestDashboardStats:
    def test_stats_leer(self, admin_client):
        """Dashboard-Stats bei leerer DB geben 0-Werte zurück."""
        res = admin_client.get("/api/v1/dashboard/stats")
        assert res.status_code == 200
        data = res.json()
        assert data["customers"] == 0
        assert data["invoices"] == 0
        assert data["overdue_invoices"] == 0
        assert data["low_stock"] == 0

    def test_stats_mit_kunden(self, admin_client, sample_customer):
        """Kundenzähler steigt mit aktivem Kunden."""
        res = admin_client.get("/api/v1/dashboard/stats")
        data = res.json()
        assert data["customers"] >= 1

    def test_stats_ueberfaellige_rechnungen(self, admin_client, sample_invoice):
        """Überfällige Rechnungen werden korrekt gezählt."""
        res = admin_client.get("/api/v1/dashboard/stats")
        data = res.json()
        # sample_invoice hat due_date in der Vergangenheit und Status "issued"
        assert data["overdue_invoices"] >= 1

    def test_stats_ohne_auth(self, client):
        """Ohne Authentifizierung → 401/403."""
        res = client.get("/api/v1/dashboard/stats")
        assert res.status_code in (401, 403)

    def test_stats_werkstatt_benutzer(self, werkstatt_client):
        """Werkstatt-Benutzer kann Stats abrufen."""
        res = werkstatt_client.get("/api/v1/dashboard/stats")
        assert res.status_code == 200
