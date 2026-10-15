"""Tests: Zwei-Faktor-Anmeldung (TOTP), Wiederherstellungscodes, Server-Einstellungen."""

import pyotp
import pytest

API = "/api/v1"


@pytest.fixture()
def require_2fa(monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "TWO_FACTOR_REQUIRED", True)


def _login(client, email="testadmin@warevision.test", password="testpass123"):
    return client.post(f"{API}/auth/login", json={"email": email, "password": password})


def _setup(client, admin_user):
    """Kompletten Einrichtungsablauf durchspielen; gibt (secret, recovery_codes, access_token) zurück."""
    res = _login(client)
    assert res.status_code == 200
    body = res.json()
    assert body["two_factor_setup_required"] and body["access_token"] is None
    challenge = body["challenge_token"]
    start = client.post(f"{API}/auth/2fa/setup/start", json={"challenge_token": challenge}).json()
    assert start["otpauth_uri"].startswith("otpauth://totp/WareVision:")
    assert start["qr_data_uri"].startswith("data:image/svg+xml") and "xmlns" in start["qr_data_uri"]
    secret = start["secret"]
    conf = client.post(f"{API}/auth/2fa/setup/confirm",
                       json={"challenge_token": challenge, "code": pyotp.TOTP(secret).now()})
    assert conf.status_code == 200, conf.text
    data = conf.json()
    assert len(data["recovery_codes"]) == 10
    return secret, data["recovery_codes"], data["access_token"]


def _next_code(secret: str) -> str:
    """Code des nächsten Zeitfensters (der aktuelle wurde bei der Einrichtung schon benutzt)."""
    totp = pyotp.TOTP(secret)
    import time
    return totp.at(int(time.time()) + 30)


class TestOhne2FA:
    def test_login_direkt_mit_token(self, client, admin_user):
        body = _login(client).json()
        assert body["access_token"] and not body["two_factor_required"] and not body["two_factor_setup_required"]


class TestEinrichtungUndAnmeldung:
    def test_einrichtung_und_anmeldung_mit_code(self, client, admin_user, require_2fa, db):
        secret, codes, token = _setup(client, admin_user)
        me = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        db.refresh(admin_user)
        assert admin_user.totp_enabled and admin_user.totp_secret and secret not in admin_user.totp_secret
        assert admin_user.recovery_codes and codes[0] not in str(admin_user.recovery_codes)

        body = _login(client).json()
        assert body["two_factor_required"] and body["access_token"] is None
        bad = client.post(f"{API}/auth/2fa/verify", json={"challenge_token": body["challenge_token"], "code": "000000"})
        assert bad.status_code == 401
        ok = client.post(f"{API}/auth/2fa/verify",
                         json={"challenge_token": body["challenge_token"], "code": _next_code(secret)})
        assert ok.status_code == 200 and ok.json()["access_token"]

    def test_code_nur_einmal_gueltig(self, client, admin_user, require_2fa):
        secret, _, _ = _setup(client, admin_user)
        code = _next_code(secret)
        ch = _login(client).json()["challenge_token"]
        assert client.post(f"{API}/auth/2fa/verify", json={"challenge_token": ch, "code": code}).status_code == 200
        ch = _login(client).json()["challenge_token"]
        assert client.post(f"{API}/auth/2fa/verify", json={"challenge_token": ch, "code": code}).status_code == 401

    def test_wiederherstellungscode_einmalig(self, client, admin_user, require_2fa, db):
        _, codes, _ = _setup(client, admin_user)
        ch = _login(client).json()["challenge_token"]
        res = client.post(f"{API}/auth/2fa/verify", json={"challenge_token": ch, "recovery_code": codes[0].lower()})
        assert res.status_code == 200
        ch = _login(client).json()["challenge_token"]
        assert client.post(f"{API}/auth/2fa/verify",
                           json={"challenge_token": ch, "recovery_code": codes[0]}).status_code == 401
        db.refresh(admin_user)
        assert len(admin_user.recovery_codes) == 9

    def test_falscher_code_bei_einrichtung(self, client, admin_user, require_2fa, db):
        ch = _login(client).json()["challenge_token"]
        client.post(f"{API}/auth/2fa/setup/start", json={"challenge_token": ch})
        res = client.post(f"{API}/auth/2fa/setup/confirm", json={"challenge_token": ch, "code": "123456"})
        assert res.status_code == 400
        db.refresh(admin_user)
        assert not admin_user.totp_enabled

    def test_zwischentoken_ist_kein_zugang(self, client, admin_user, require_2fa):
        ch = _login(client).json()["challenge_token"]
        assert client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {ch}"}).status_code == 401
        # Einrichtungs-Token taugt nicht zur Code-Prüfung und umgekehrt
        assert client.post(f"{API}/auth/2fa/verify", json={"challenge_token": ch, "code": "123456"}).status_code == 401

    def test_falsches_passwort_kein_zwischentoken(self, client, admin_user, require_2fa):
        res = _login(client, password="falsch-falsch")
        assert res.status_code == 401

    def test_einmal_eingerichtet_gilt_auch_ohne_pflicht(self, client, admin_user, require_2fa, monkeypatch):
        _setup(client, admin_user)
        from app.core.config import get_settings
        monkeypatch.setattr(get_settings(), "TWO_FACTOR_REQUIRED", False)
        assert _login(client).json()["two_factor_required"]


class TestVerwaltung:
    def test_status_und_neue_codes(self, client, admin_user, require_2fa):
        secret, old_codes, token = _setup(client, admin_user)
        h = {"Authorization": f"Bearer {token}"}
        st = client.get(f"{API}/auth/2fa/status", headers=h).json()
        assert st == {**st, "enabled": True, "required": True, "recovery_codes_left": 10}
        assert client.post(f"{API}/auth/2fa/recovery-codes", json={"code": "000000"}, headers=h).status_code == 400
        new = client.post(f"{API}/auth/2fa/recovery-codes", json={"code": _next_code(secret)}, headers=h)
        assert new.status_code == 200 and len(new.json()) == 10 and set(new.json()).isdisjoint(old_codes)

    def test_admin_setzt_2fa_zurueck(self, client, admin_user, werkstatt_user, require_2fa, db):
        from app.core.security import create_access_token
        werkstatt_user.totp_enabled = True
        werkstatt_user.totp_secret = "x"
        db.flush()
        h = {"Authorization": f"Bearer {create_access_token(str(admin_user.id))}"}
        res = client.post(f"{API}/users/{werkstatt_user.id}/reset-2fa", headers=h)
        assert res.status_code == 200 and res.json()["totp_enabled"] is False
        body = _login(client, "testwerkstatt@warevision.test", "werkstattpass123").json()
        assert body["two_factor_setup_required"]
        h2 = {"Authorization": f"Bearer {create_access_token(str(werkstatt_user.id))}"}
        assert client.post(f"{API}/users/{admin_user.id}/reset-2fa", headers=h2).status_code == 403

    def test_unlesbares_geheimnis_meldet_klar(self, client, admin_user, db):
        admin_user.totp_enabled = True
        admin_user.totp_secret = "kaputt"
        db.flush()
        ch = _login(client).json()["challenge_token"]
        res = client.post(f"{API}/auth/2fa/verify", json={"challenge_token": ch, "code": "123456"})
        assert res.status_code == 409 and "Admin" in res.json()["detail"]


class TestServerEinstellungen:
    def test_unsichere_einstellungen_werden_erkannt(self):
        from app.core.config import Settings
        s = Settings(APP_ENV="production", SECRET_KEY="kurz", PUBLIC_URL="http://x.de",
                     DATABASE_URL="postgresql://warevision:warevision@db/warevision")
        problems = " ".join(s.production_problems())
        assert "SECRET_KEY" in problems and "Standardpasswort" in problems and "https" in problems
        ok = Settings(APP_ENV="production", SECRET_KEY="x" * 40, PUBLIC_URL="https://kunde.warevision.de",
                      DATABASE_URL="postgresql://wv:geheim@db/warevision")
        assert ok.production_problems() == []
        assert ok.two_factor_required
        assert ok.cors_origins_resolved == ["https://kunde.warevision.de"]

    def test_standardpasswort_auf_server_gesperrt(self, client, db, monkeypatch):
        from app.core.config import get_settings
        from app.core.security import get_password_hash
        from app.models.role import Role
        from app.models.user import User
        role = db.query(Role).filter(Role.name == "admin").first()
        db.add(User(role_id=role.id, first_name="A", last_name="B", email="std@warevision.test",
                    password_hash=get_password_hash("admin123")))
        db.flush()
        monkeypatch.setattr(get_settings(), "APP_ENV", "production")
        res = _login(client, "std@warevision.test", "admin123")
        assert res.status_code == 403 and "Standardpasswort" in res.json()["detail"]

    def test_registrierung_abschaltbar(self, client, monkeypatch):
        from app.core.config import get_settings
        monkeypatch.setattr(get_settings(), "REGISTRATION_ENABLED", False)
        res = client.post(f"{API}/auth/register", json={"email": "neu@x.de", "first_name": "A", "last_name": "B",
                                                         "password": "langespasswort1"})
        assert res.status_code == 404

    def test_passwort_mindestens_10_zeichen(self, admin_client):
        res = admin_client.post(f"{API}/auth/change-password",
                                json={"current_password": "testpass123", "new_password": "kurz12345"})
        assert res.status_code == 400 and "10" in res.json()["detail"]
