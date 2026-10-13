"""Tests: Authentifizierung."""

import pytest


class TestLogin:
    def test_login_erfolg(self, client, admin_user):
        """Korrektes Login liefert JWT-Token zurück."""
        res = client.post("/api/v1/auth/login", json={
            "email": "testadmin@warevision.test",
            "password": "testpass123",
        })
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_falsches_passwort(self, client, admin_user):
        """Falsches Passwort → 401."""
        res = client.post("/api/v1/auth/login", json={
            "email": "testadmin@warevision.test",
            "password": "falschespasswort",
        })
        assert res.status_code == 401

    def test_login_unbekannte_email(self, client):
        """Unbekannte E-Mail → 401."""
        res = client.post("/api/v1/auth/login", json={
            "email": "niemand@warevision.test",
            "password": "egal",
        })
        assert res.status_code == 401

    def test_login_inaktiver_benutzer(self, client, db):
        """Inaktiver Benutzer kann sich nicht anmelden."""
        from app.models.role import Role
        from app.models.user import User
        from app.core.security import get_password_hash

        role = db.query(Role).filter(Role.name == "werkstatt").first()
        user = User(
            role_id=role.id,
            first_name="Inaktiv",
            last_name="User",
            email="inaktiv@warevision.test",
            password_hash=get_password_hash("geheim123"),
            is_active=False,
        )
        db.add(user)
        db.flush()

        res = client.post("/api/v1/auth/login", json={
            "email": "inaktiv@warevision.test",
            "password": "geheim123",
        })
        assert res.status_code in (401, 403)  # 403: Konto deaktiviert


class TestMe:
    def test_get_me(self, admin_client, admin_user):
        """GET /auth/me gibt den angemeldeten Benutzer zurück."""
        res = admin_client.get("/api/v1/auth/me")
        assert res.status_code == 200
        data = res.json()
        assert data["email"] == "testadmin@warevision.test"
        assert data["role_name"] == "admin"

    def test_get_me_ohne_token(self, client):
        """Ohne Token → 403 oder 401."""
        res = client.get("/api/v1/auth/me")
        assert res.status_code in (401, 403)

    def test_get_me_ungültiger_token(self, client):
        """Ungültiger Token → 401."""
        client.headers.update({"Authorization": "Bearer invalid.token.here"})
        res = client.get("/api/v1/auth/me")
        assert res.status_code == 401


class TestPasswortAendern:
    def test_passwort_aendern_erfolg(self, admin_client):
        """Passwort ändern mit korrektem alten Passwort."""
        res = admin_client.post("/api/v1/auth/change-password", json={
            "current_password": "testpass123",
            "new_password": "neuespasswort456",
        })
        assert res.status_code == 200

    def test_passwort_aendern_falsches_altes_passwort(self, admin_client):
        """Falsches altes Passwort → 400."""
        res = admin_client.post("/api/v1/auth/change-password", json={
            "current_password": "falsch",
            "new_password": "neuespasswort456",
        })
        assert res.status_code == 400

    def test_passwort_zu_kurz(self, admin_client):
        """Neues Passwort zu kurz → 422 (Validierungsfehler)."""
        res = admin_client.post("/api/v1/auth/change-password", json={
            "current_password": "testpass123",
            "new_password": "ab",
        })
        assert res.status_code in (400, 422)
