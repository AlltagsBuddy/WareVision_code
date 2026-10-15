"""Tests: Barcode einem Artikel zuordnen und beim nächsten Scan wiederfinden."""

API = "/api/v1/articles"


def _article(client, nr, barcode=None):
    data = {"article_number": nr, "name": f"Teil {nr}"}
    if barcode:
        data["barcode"] = barcode
    res = client.post(API, json=data)
    assert res.status_code == 201, res.text
    return res.json()


class TestZuordnen:
    def test_unbekannt_dann_zuordnen_dann_gefunden(self, admin_client):
        a = _article(admin_client, "B-1")
        assert admin_client.get(f"{API}/barcode/4006381333931").status_code == 404
        res = admin_client.post(f"{API}/{a['id']}/barcode", json={"barcode": " 4006381333931 "})
        assert res.status_code == 200 and res.json()["barcode"] == "4006381333931"
        hit = admin_client.get(f"{API}/barcode/4006381333931")
        assert hit.status_code == 200 and hit.json()["id"] == a["id"]
        assert [x["id"] for x in admin_client.get(API, params={"barcode": "4006381333931"}).json()] == [a["id"]]

    def test_upc_und_ean_variante(self, admin_client):
        a = _article(admin_client, "B-2", "012345678905")
        assert admin_client.get(f"{API}/barcode/0012345678905").json()["id"] == a["id"]

    def test_barcode_gehoert_schon_anderem_artikel(self, admin_client):
        _article(admin_client, "B-3", "111")
        b = _article(admin_client, "B-4")
        res = admin_client.post(f"{API}/{b['id']}/barcode", json={"barcode": "111"})
        assert res.status_code == 409 and "B-3" in res.json()["detail"]
        assert admin_client.post(API, json={"article_number": "B-5", "name": "x", "barcode": "111"}).status_code == 409

    def test_ersetzen_nur_mit_bestaetigung(self, admin_client, db):
        from app.models.audit_log import AuditLog
        a = _article(admin_client, "B-6", "222")
        res = admin_client.post(f"{API}/{a['id']}/barcode", json={"barcode": "333"})
        assert res.status_code == 409 and "222" in res.json()["detail"]
        res = admin_client.post(f"{API}/{a['id']}/barcode", json={"barcode": "333", "replace": True})
        assert res.status_code == 200 and res.json()["barcode"] == "333"
        assert db.query(AuditLog).filter(AuditLog.action == "barcode_assign").count() == 1

    def test_gleicher_code_nochmal_ist_ok(self, admin_client):
        a = _article(admin_client, "B-7", "444")
        assert admin_client.post(f"{API}/{a['id']}/barcode", json={"barcode": "444"}).status_code == 200

    def test_mitarbeiter_darf_nicht_zuordnen(self, client, db, admin_client):
        from app.core.security import create_access_token, get_password_hash
        from app.models.role import Role
        from app.models.user import User
        a = _article(admin_client, "B-8")
        role = db.query(Role).filter(Role.name == "mitarbeiter").first()
        u = User(role_id=role.id, first_name="M", last_name="A", email="ma2@warevision.test",
                 password_hash=get_password_hash("geheim12345"))
        db.add(u)
        db.flush()
        h = {"Authorization": f"Bearer {create_access_token(str(u.id))}"}
        assert client.post(f"{API}/{a['id']}/barcode", json={"barcode": "555"}, headers=h).status_code == 403
