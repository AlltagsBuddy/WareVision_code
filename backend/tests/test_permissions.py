"""Tests: Fünf Rollen, Rechte je Bereich (sehen/ändern) und Sonderrechte – serverseitig geprüft."""

import pytest

API = "/api/v1"


def _make_user(db, role_name: str, email: str, permissions=None):
    from app.core.security import get_password_hash
    from app.models.role import Role
    from app.models.user import User

    role = db.query(Role).filter(Role.name == role_name).first()
    user = User(role_id=role.id, first_name="T", last_name=role_name, email=email,
                password_hash=get_password_hash("geheim12345"), permissions=permissions)
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


def _headers(user):
    from app.core.security import create_access_token
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


def _role_id(admin_client, name):
    return next(r["id"] for r in admin_client.get(f"{API}/users/roles").json() if r["name"] == name)


@pytest.fixture()
def customer(admin_client):
    res = admin_client.post(f"{API}/customers", json={"customer_type": "B2C", "first_name": "Max",
                                                      "last_name": "Muster"})
    assert res.status_code == 201, res.text
    return res.json()


class TestRollen:
    def test_fuenf_rollen_mit_bezeichnung(self, admin_client):
        roles = admin_client.get(f"{API}/users/roles").json()
        assert [r["name"] for r in roles] == ["admin", "chef", "buero", "werkstatt", "mitarbeiter"]
        assert [r["label"] for r in roles][:2] == ["Administrator", "Chef/Chefin"]
        assert roles[0]["is_manager"] and roles[1]["is_manager"] and not roles[2]["is_manager"]
        assert roles[4]["template"]["appointments"] == {"visible": True, "write": True}
        assert roles[4]["template"]["customers"] == {"visible": True, "write": False}

    def test_katalog(self, admin_client):
        cat = admin_client.get(f"{API}/users/permission-catalog").json()
        assert {"key": "customers", "label": "Kunden"} in cat["modules"]
        assert "dsgvo_delete" in [r["key"] for r in cat["rights"]]

    def test_chef_hat_gleiche_rechte_wie_admin(self, client, db, customer):
        chef = _make_user(db, "chef", "chef@warevision.test")
        h = _headers(chef)
        assert client.get(f"{API}/users", headers=h).status_code == 200
        assert client.get(f"{API}/incoming-invoices", headers=h).status_code == 200
        assert client.get(f"{API}/customers/{customer['id']}/export", headers=h).status_code == 200
        me = client.get(f"{API}/auth/me", headers=h).json()
        assert me["is_manager"] and me["role_label"] == "Chef/Chefin"
        assert all(me["permissions"]["rights"].values())

    def test_neuer_benutzer_bekommt_vorlage(self, admin_client):
        res = admin_client.post(f"{API}/users", json={
            "email": "neu@warevision.test", "first_name": "N", "last_name": "M", "password": "geheim12345",
            "role_id": _role_id(admin_client, "mitarbeiter")})
        assert res.status_code == 201, res.text
        p = res.json()["permissions"]
        assert p["workshop_orders"]["write"] and not p["invoices"]["visible"] and not p["customers"]["write"]
        assert res.json()["role_label"] == "Mitarbeiter" and not any(p["rights"].values())


class TestMitarbeiter:
    @pytest.fixture()
    def h(self, db):
        return _headers(_make_user(db, "mitarbeiter", "ma@warevision.test"))

    def test_lesen_ja_aendern_nein(self, client, h, customer):
        assert client.get(f"{API}/customers", headers=h).status_code == 200
        res = client.patch(f"{API}/customers/{customer['id']}", json={"notes": "x"}, headers=h)
        assert res.status_code == 403
        assert client.post(f"{API}/customers", json={"customer_type": "B2C", "last_name": "Y"},
                           headers=h).status_code == 403

    def test_gesperrte_bereiche(self, client, h):
        assert client.get(f"{API}/invoices", headers=h).status_code == 403
        assert client.get(f"{API}/quotes", headers=h).status_code == 403
        assert client.get(f"{API}/incoming-invoices", headers=h).status_code == 403
        assert client.get(f"{API}/accounting/export", headers=h).status_code == 403
        assert client.get(f"{API}/users", headers=h).status_code == 403

    def test_termine_bearbeiten(self, client, h):
        assert client.get(f"{API}/appointments", headers=h).status_code == 200

    def test_keine_dsgvo(self, client, h, customer):
        assert client.get(f"{API}/customers/{customer['id']}/export", headers=h).status_code == 403
        assert client.post(f"{API}/customers/{customer['id']}/dsgvo-delete", headers=h).status_code == 403


class TestSonderrechte:
    def test_dsgvo_export_einzeln_freigeben(self, client, db, customer):
        from app.core.permissions import ROLE_TEMPLATES
        import copy
        perms = copy.deepcopy(ROLE_TEMPLATES["mitarbeiter"])
        perms["rights"]["dsgvo_export"] = True
        u = _make_user(db, "mitarbeiter", "dsgvo@warevision.test", perms)
        h = _headers(u)
        assert client.get(f"{API}/customers/{customer['id']}/export", headers=h).status_code == 200
        assert client.post(f"{API}/customers/{customer['id']}/dsgvo-delete", headers=h).status_code == 403

    def test_buchhaltung_bringt_lesen_der_rechnungen(self, client, db):
        u = _make_user(db, "mitarbeiter", "bh@warevision.test", {
            "invoices": {"visible": False, "write": False}, "rights": {"accounting": True}})
        h = _headers(u)
        assert client.get(f"{API}/incoming-invoices", headers=h).status_code == 200
        assert client.get(f"{API}/invoices", headers=h).status_code == 200
        assert client.post(f"{API}/invoices", json={}, headers=h).status_code == 403

    def test_buero_vorlage_rechnungen_aber_keine_buchhaltung(self, client, db):
        h = _headers(_make_user(db, "buero", "buero@warevision.test"))
        assert client.get(f"{API}/invoices", headers=h).status_code == 200
        assert client.get(f"{API}/incoming-invoices", headers=h).status_code == 403

    def test_auswahllisten_aus_anderem_bereich(self, client, db):
        # Nur Werkstattaufträge freigegeben → Kunden und Artikel dürfen gelesen werden (Auswahl), nicht geändert
        perms = {m: {"visible": m == "workshop_orders", "write": m == "workshop_orders"}
                 for m in ("customers", "vehicles", "articles", "suppliers", "stock", "stock_counts",
                           "purchase_orders", "quotes", "workshop_orders", "maintenance_plans",
                           "appointments", "invoices", "documents")}
        h = _headers(_make_user(db, "werkstatt", "wo@warevision.test", perms))
        assert client.get(f"{API}/customers", headers=h).status_code == 200
        assert client.get(f"{API}/articles", headers=h).status_code == 200
        assert client.post(f"{API}/customers", json={"customer_type": "B2C", "last_name": "Y"},
                           headers=h).status_code == 403
        assert client.get(f"{API}/suppliers", headers=h).status_code == 403


class TestVerwaltung:
    def test_nur_leitung_verwaltet_benutzer(self, client, db):
        h = _headers(_make_user(db, "buero", "b2@warevision.test"))
        assert client.post(f"{API}/users", json={}, headers=h).status_code == 403

    def test_letzte_leitung_bleibt(self, admin_client, admin_user, db):
        other = _make_user(db, "werkstatt", "w2@warevision.test")
        # Admin darf sich nicht selbst zur Werkstatt machen, solange niemand sonst leitet
        res = admin_client.patch(f"{API}/users/{admin_user.id}",
                                 json={"role_id": _role_id(admin_client, "werkstatt")})
        assert res.status_code == 400 and "mindestens ein" in res.json()["detail"]
        db.refresh(admin_user)
        assert admin_user.role.name == "admin"
        # Mit einer Chefin geht es
        _make_user(db, "chef", "chefin@warevision.test")
        res = admin_client.patch(f"{API}/users/{admin_user.id}",
                                 json={"role_id": _role_id(admin_client, "buero")})
        assert res.status_code == 200 and res.json()["role_name"] == "buero"
        assert other.is_active

    def test_rechte_aendern_wird_protokolliert(self, admin_client, db):
        from app.models.audit_log import AuditLog
        u = _make_user(db, "mitarbeiter", "log@warevision.test")
        perms = admin_client.get(f"{API}/users").json()
        perms = next(x for x in perms if x["id"] == str(u.id))["permissions"]
        perms["rights"]["invoices_manage"] = True
        res = admin_client.patch(f"{API}/users/{u.id}", json={"permissions": perms})
        assert res.status_code == 200 and res.json()["permissions"]["rights"]["invoices_manage"]
        assert db.query(AuditLog).filter(AuditLog.entity_id == u.id, AuditLog.action == "user_update").count() == 1

    def test_unbekannte_rechte_werden_verworfen(self, admin_client, db):
        u = _make_user(db, "mitarbeiter", "x@warevision.test")
        res = admin_client.patch(f"{API}/users/{u.id}", json={"permissions": {"rights": {"root": True}}})
        p = res.json()["permissions"]
        assert "root" not in p["rights"] and not p["customers"]["visible"]

    def test_leitung_ohne_einzelrechte(self, admin_client, db):
        u = _make_user(db, "mitarbeiter", "y@warevision.test")
        res = admin_client.patch(f"{API}/users/{u.id}", json={"role_id": _role_id(admin_client, "chef")})
        assert res.status_code == 200 and res.json()["is_manager"]
        db.refresh(u)
        assert u.permissions is None


class TestOeffentlich:
    def test_webhook_ohne_anmeldung(self, client):
        assert client.get(f"{API}/appointments/webhook/termin-marktplatz/ping").status_code == 200

    def test_ohne_anmeldung_gesperrt(self, client):
        assert client.get(f"{API}/customers").status_code in (401, 403)
