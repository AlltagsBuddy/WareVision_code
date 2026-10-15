"""Tests: Benutzer, Registrierung, Datenexport (DSGVO), Audit-Log, Buchhaltungsexport, Einstellungen, Webhook."""

import io
import zipfile

import pytest

V1 = "/api/v1"


class TestBenutzer:
    def test_anlegen_aendern_deaktivieren(self, admin_client):
        roles = admin_client.get(f"{V1}/users/roles").json()
        werkstatt = next(r for r in roles if r["name"] == "werkstatt")
        res = admin_client.post(f"{V1}/users", json={"email": "mech@test.de", "first_name": "Max", "last_name": "Mech",
                                                     "password": "geheim12345", "role_id": werkstatt["id"]})
        assert res.status_code == 201, res.text
        uid = res.json()["id"]
        assert res.json()["role_name"] == "werkstatt"
        assert admin_client.post(f"{V1}/users", json={"email": "mech@test.de", "first_name": "A", "last_name": "B",
                                                      "password": "geheim12345", "role_id": werkstatt["id"]}).status_code == 409
        res = admin_client.patch(f"{V1}/users/{uid}", json={"permissions": {"invoices": {"visible": False, "write": False}}})
        assert res.json()["permissions"]["invoices"]["visible"] is False
        assert admin_client.delete(f"{V1}/users/{uid}").status_code == 204
        user = next(u for u in admin_client.get(f"{V1}/users").json() if u["id"] == uid)
        assert user["is_active"] is False  # deaktiviert, nicht gelöscht

    def test_selbst_deaktivieren_verboten(self, admin_client, admin_user):
        assert admin_client.delete(f"{V1}/users/{admin_user.id}").status_code == 400

    def test_kurzes_passwort(self, admin_client):
        role = admin_client.get(f"{V1}/users/roles").json()[0]
        res = admin_client.post(f"{V1}/users", json={"email": "x@test.de", "first_name": "A", "last_name": "B",
                                                     "password": "123", "role_id": role["id"]})
        assert res.status_code == 422

    def test_werkstatt_keine_benutzerverwaltung(self, werkstatt_client):
        assert werkstatt_client.get(f"{V1}/users").status_code == 403


class TestRegistrierungUndExport:
    def test_registrierung_inaktiv(self, client, db):
        from app.models.user import User

        res = client.post(f"{V1}/auth/register", json={"email": "Neu@Test.de", "first_name": "Neu", "last_name": "Nutzer",
                                                       "password": "geheim12345"})
        assert res.status_code in (200, 201), res.text
        user = db.query(User).filter(User.email == "neu@test.de").first()
        assert user is not None and user.is_active is False  # Freischaltung durch Admin nötig
        login = client.post(f"{V1}/auth/login", json={"email": "neu@test.de", "password": "geheim12345"})
        assert login.status_code in (401, 403)

    def test_registrierung_doppelt(self, client, admin_user):
        res = client.post(f"{V1}/auth/register", json={"email": admin_user.email, "first_name": "A", "last_name": "B",
                                                       "password": "geheim12345"})
        assert res.status_code == 409

    def test_dsgvo_export_eigene_daten(self, admin_client, admin_user):
        data = admin_client.get(f"{V1}/auth/me/export").json()
        assert data["user"]["email"] == admin_user.email
        assert "password" not in str(data).lower()


class TestAuditLog:
    def test_aktionen_protokolliert(self, admin_client, sample_customer):
        admin_client.post(f"{V1}/quotes", json={
            "customer_id": str(sample_customer.id), "quote_date": "2026-10-13",
            "items": [{"description": "Test", "quantity": 1, "unit_price": 1, "vat_rate": 19}],
        })
        res = admin_client.get(f"{V1}/audit-logs")
        assert res.status_code == 200
        body = res.json()
        entries = body if isinstance(body, list) else body.get("items", [])
        assert any(e.get("entity_type") == "quote" and e.get("action") == "create" for e in entries)

    def test_nur_admin(self, werkstatt_client):
        assert werkstatt_client.get(f"{V1}/audit-logs").status_code == 403


class TestBuchhaltungsexport:
    def test_zip_mit_csv_und_pdfs(self, admin_client, sample_invoice, company_settings):
        res = admin_client.get(f"{V1}/accounting/export?date_from=2026-01-01&date_to=2026-12-31")
        assert res.status_code == 200, res.text
        z = zipfile.ZipFile(io.BytesIO(res.content))
        names = z.namelist()
        assert any(n.startswith("ausgangsrechnungen_privat/") and n.endswith(".pdf") for n in names)
        csv_name = next(n for n in names if n.endswith(".csv") and "privat" in n)
        csv = z.read(csv_name).decode("utf-8-sig")
        assert "RE-TEST-0001" in csv and "119,00" in csv

    def test_datum_umgekehrt(self, admin_client):
        assert admin_client.get(f"{V1}/accounting/export?date_from=2026-12-31&date_to=2026-01-01").status_code == 400

    def test_nur_admin(self, werkstatt_client):
        assert werkstatt_client.get(f"{V1}/accounting/export?date_from=2026-01-01&date_to=2026-12-31").status_code == 403


class TestEinstellungen:
    def test_befreiungshinweis_speichern(self, admin_client):
        res = admin_client.patch(f"{V1}/settings", json={"invoice_vat_exemption_note": "Durchlaufender Posten"})
        assert res.status_code == 200
        assert res.json()["invoice_vat_exemption_note"] == "Durchlaufender Posten"

    def test_ki_schluessel_wird_nie_angezeigt(self, admin_client):
        res = admin_client.patch(f"{V1}/settings", json={"ai_help_api_key": "sk-ant-geheim-123", "ai_help_model": "claude-haiku-5-5"})
        assert res.status_code == 200
        assert res.json()["ai_help_api_key"] == "********"
        assert res.json()["ai_help_configured"] is True
        assert "sk-ant-geheim" not in admin_client.get(f"{V1}/settings").text
        # leeres Feld = Schlüssel bleibt erhalten
        assert admin_client.patch(f"{V1}/settings", json={"ai_help_api_key": ""}).json()["ai_help_configured"] is True
        # gezielt entfernen
        assert admin_client.patch(f"{V1}/settings", json={"ai_help_api_key_remove": True}).json()["ai_help_configured"] is False

    def test_logo_hochladen(self, admin_client, tmp_path, monkeypatch):
        from PIL import Image

        monkeypatch.setattr("app.api.v1.settings._UPLOAD_DIR", str(tmp_path))
        buf = io.BytesIO()
        Image.new("RGB", (40, 20), "red").save(buf, format="PNG")
        res = admin_client.post(f"{V1}/settings/logo", files={"file": ("logo.png", buf.getvalue(), "image/png")})
        assert res.status_code == 200, res.text
        assert admin_client.get(f"{V1}/settings/logo").status_code == 200

    def test_logo_falscher_typ(self, admin_client):
        res = admin_client.post(f"{V1}/settings/logo", files={"file": ("x.txt", b"abc", "text/plain")})
        assert res.status_code == 400

    def test_nur_admin(self, werkstatt_client):
        assert werkstatt_client.patch(f"{V1}/settings", json={"company_name": "X"}).status_code == 403


class TestTerminmarktplatzWebhook:
    URL = f"{V1}/appointments/webhook/termin-marktplatz"

    def _set_key(self, db, key="tm-test-key"):
        from app.models.app_setting import AppSetting
        db.add(AppSetting(key="termin_marktplatz_api_key", value=key))
        db.flush()

    def test_ping(self, client):
        assert client.get(f"{self.URL}/ping").json()["status"] == "ok"

    def test_nicht_konfiguriert(self, client):
        assert client.post(self.URL, json={}, headers={"X-API-Key": "x"}).status_code == 503

    def test_falscher_schluessel(self, client, db):
        self._set_key(db)
        assert client.post(self.URL, json={}, headers={"X-API-Key": "falsch"}).status_code == 401

    def test_buchung_anlegen_und_dublette(self, client, db):
        self._set_key(db)
        body = {
            "external_booking_id": "TM-TEST-1",
            "starts_at": "2026-11-02T10:00:00+01:00",
            "ends_at": "2026-11-02T11:00:00+01:00",
            "customer_first_name": "Erika",
            "customer_last_name": "Muster",
            "customer_email": "erika@test.de",
        }
        res = client.post(self.URL, json=body, headers={"X-API-Key": "tm-test-key"})
        assert res.status_code == 200, res.text
        first = res.json()
        assert first["source"] == "termin_marktplatz"
        assert first["customer_last_name"] == "Muster"
        again = client.post(self.URL, json=body, headers={"Authorization": "Bearer tm-test-key"}).json()
        assert again["id"] == first["id"]  # Dublettenschutz über externe ID

    def test_unvollstaendige_daten(self, client, db):
        self._set_key(db)
        res = client.post(self.URL, json={"external_booking_id": "X"}, headers={"X-API-Key": "tm-test-key"})
        assert res.status_code in (400, 422)
