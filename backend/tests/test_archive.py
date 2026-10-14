"""Tests: Belegarchiv (GoBD) – ausgegebene Belege bleiben unverändert, Prüfsumme, Nachziehen, Prüfung."""

import io
import os
import stat
import zipfile
from pathlib import Path

import pytest

INV = "/api/v1/invoices"
ARC = "/api/v1/archive"
ITEMS = [{"description": "Inspektion", "quantity": 1, "unit": "Std.", "unit_price": 100, "vat_rate": 19}]


def _text(pdf: bytes) -> str:
    from pypdf import PdfReader
    return "".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)


def _invoice(client, customer, issue=True):
    res = client.post(INV, json={"customer_id": str(customer.id), "invoice_date": "2026-10-13", "items": ITEMS})
    assert res.status_code == 201, res.text
    inv = res.json()
    if issue:
        assert client.post(f"{INV}/{inv['id']}/issue").status_code == 200
    return inv


def _docs(db, entity_id):
    from app.models.archived_document import ArchivedDocument
    return {d.kind: d for d in db.query(ArchivedDocument).filter(ArchivedDocument.entity_id == entity_id).all()}


def _set_company(db, name):
    from app.models.app_setting import AppSetting
    row = db.query(AppSetting).filter(AppSetting.key == "company_name").first()
    row.value = name
    db.flush()


class TestRechnungsarchiv:
    def test_ausstellen_archiviert_pdf_und_zugferd(self, admin_client, db, sample_customer, company_settings):
        inv = _invoice(admin_client, sample_customer)
        docs = _docs(db, inv["id"])
        assert set(docs) == {"pdf", "zugferd"}
        pdf = docs["pdf"]
        assert len(pdf.sha256) == 64 and not pdf.backfilled
        assert Path(pdf.file_path).read_bytes() == admin_client.get(f"{INV}/{inv['id']}/pdf").content
        assert not os.stat(pdf.file_path).st_mode & stat.S_IWUSR   # schreibgeschützt

    def test_entwurf_wird_nicht_archiviert(self, admin_client, db, sample_customer):
        inv = _invoice(admin_client, sample_customer, issue=False)
        admin_client.get(f"{INV}/{inv['id']}/pdf")
        assert _docs(db, inv["id"]) == {}

    def test_spaetere_aenderungen_aendern_ausgestellte_rechnung_nicht(self, admin_client, db, sample_customer, company_settings):
        inv = _invoice(admin_client, sample_customer)
        before = admin_client.get(f"{INV}/{inv['id']}/pdf").content
        old_name = sample_customer.last_name
        _set_company(db, "Neue Firma GmbH")
        sample_customer.last_name = "Geändert"
        db.flush()
        after = admin_client.get(f"{INV}/{inv['id']}/pdf").content
        assert after == before                                   # byte-genau das Original
        assert "Neue Firma" not in _text(after) and old_name in _text(after)
        zugferd = admin_client.get(f"{INV}/{inv['id']}/zugferd").content
        assert "Neue Firma" not in _text(zugferd)
        # ein neuer Entwurf zeigt dagegen die aktuellen Daten
        draft = _invoice(admin_client, sample_customer, issue=False)
        assert "Neue Firma" in _text(admin_client.get(f"{INV}/{draft['id']}/pdf").content)

    def test_dsgvo_anonymisierung_aendert_rechnung_nicht(self, admin_client, sample_customer, company_settings):
        inv = _invoice(admin_client, sample_customer)
        name = sample_customer.last_name
        res = admin_client.post(f"/api/v1/customers/{sample_customer.id}/dsgvo-delete")
        assert res.status_code == 200 and res.json()["action"] == "anonymized"
        assert name in _text(admin_client.get(f"{INV}/{inv['id']}/pdf").content)

    def test_veraenderte_datei_wird_erkannt(self, admin_client, db, sample_customer, company_settings):
        inv = _invoice(admin_client, sample_customer)
        path = Path(_docs(db, inv["id"])["pdf"].file_path)
        os.chmod(path, 0o644)
        path.write_bytes(path.read_bytes() + b"manipuliert")
        res = admin_client.get(f"{INV}/{inv['id']}/pdf")
        assert res.status_code == 500 and "verändert" in res.json()["detail"]
        check = admin_client.get(f"{ARC}/verify").json()
        assert check["checked"] >= 2 and any("verändert" in p for p in check["problems"])

    def test_fehlende_datei_wird_nicht_neu_erzeugt(self, admin_client, db, sample_customer, company_settings):
        inv = _invoice(admin_client, sample_customer)
        path = Path(_docs(db, inv["id"])["pdf"].file_path)
        os.chmod(path, 0o644)
        path.unlink()
        res = admin_client.get(f"{INV}/{inv['id']}/pdf")
        assert res.status_code == 500 and "fehlt" in res.json()["detail"]
        assert not path.exists()

    def test_email_versendet_archiviertes_original(self, admin_client, db, sample_customer, company_settings, monkeypatch):
        sent = {}
        monkeypatch.setattr("app.services.email.send_email_with_attachment", lambda db, **kw: sent.update(kw))
        inv = _invoice(admin_client, sample_customer)
        _set_company(db, "Neue Firma GmbH")
        admin_client.post(f"{INV}/{inv['id']}/send-email", json={"recipient_email": "k@test.de"})
        assert sent["attachment_data"] == Path(_docs(db, inv["id"])["pdf"].file_path).read_bytes()

    def test_storno_und_korrektur_werden_archiviert(self, admin_client, db, sample_customer, company_settings):
        inv = _invoice(admin_client, sample_customer)
        rk = admin_client.post(f"{INV}/{inv['id']}/correction", json={
            "reason": "Kulanz", "free_lines": [{"description": "Nachlass", "net_amount": "10", "vat_rate": 19}]}).json()
        assert set(_docs(db, rk["id"])) == {"pdf", "zugferd"}
        admin_client.post(f"{INV}/{rk['id']}/cancel", json={"reason": "Irrtum"})
        sto = next(i for i in admin_client.get(INV).json() if i["invoice_number"].startswith("STO-"))
        assert set(_docs(db, sto["id"])) == {"pdf", "zugferd"}
        assert "Stornorechnung" in _text(admin_client.get(f"{INV}/{sto['id']}/pdf").content)

    def test_mahnbrief_archiviert_und_stufe_nicht_wiederholbar(self, admin_client, db, sample_customer, company_settings):
        inv = _invoice(admin_client, sample_customer)
        assert admin_client.post(f"{INV}/{inv['id']}/reminder?reminder_level=1").status_code == 200
        doc = _docs(db, inv["id"])["reminder_1"]
        _set_company(db, "Neue Firma GmbH")
        pdf = admin_client.get(f"{INV}/{inv['id']}/reminder-pdf").content
        assert pdf == Path(doc.file_path).read_bytes() and "Neue Firma" not in _text(pdf)
        res = admin_client.post(f"{INV}/{inv['id']}/reminder?reminder_level=1")
        assert res.status_code == 400 and "bereits" in res.json()["detail"]
        assert admin_client.post(f"{INV}/{inv['id']}/reminder?reminder_level=2").status_code == 200
        assert "reminder_2" in _docs(db, inv["id"])

    def test_steuerberater_export_nutzt_original(self, admin_client, db, sample_customer, company_settings):
        inv = _invoice(admin_client, sample_customer)
        original = Path(_docs(db, inv["id"])["zugferd"].file_path).read_bytes()
        _set_company(db, "Neue Firma GmbH")
        res = admin_client.get("/api/v1/accounting/export?date_from=2026-01-01&date_to=2026-12-31")
        z = zipfile.ZipFile(io.BytesIO(res.content))
        name = next(n for n in z.namelist() if n.endswith(f"{inv['invoice_number']}.pdf"))
        assert z.read(name) == original


class TestNachziehenUndUebersicht:
    def _drop_archive(self, db, entity_id):
        from app.models.archived_document import ArchivedDocument
        db.query(ArchivedDocument).filter(ArchivedDocument.entity_id == entity_id).delete()
        db.flush()

    def test_aeltere_rechnungen_nachziehen(self, admin_client, db, sample_customer, company_settings):
        inv = _invoice(admin_client, sample_customer)
        self._drop_archive(db, inv["id"])   # wie eine Rechnung von vor dem Update
        s = admin_client.get(f"{ARC}/status").json()
        assert s["missing"]["invoices"] == 1 and s["missing_total"] >= 1
        res = admin_client.post(f"{ARC}/backfill").json()
        assert res["created"]["invoices"] == 1 and res["status"]["missing_total"] == 0
        docs = _docs(db, inv["id"])
        assert docs["pdf"].backfilled and docs["zugferd"].backfilled

    def test_abruf_ohne_original_archiviert_nachtraeglich(self, admin_client, db, sample_customer, company_settings):
        inv = _invoice(admin_client, sample_customer)
        self._drop_archive(db, inv["id"])
        first = admin_client.get(f"{INV}/{inv['id']}/pdf").content
        assert _docs(db, inv["id"])["pdf"].backfilled
        _set_company(db, "Neue Firma GmbH")
        assert admin_client.get(f"{INV}/{inv['id']}/pdf").content == first

    def test_nur_admin(self, werkstatt_client):
        assert werkstatt_client.get(f"{ARC}/status").status_code == 403
        assert werkstatt_client.post(f"{ARC}/backfill").status_code == 403
        assert werkstatt_client.get(f"{ARC}/verify").status_code == 403

    def test_original_wird_nie_ueberschrieben(self, db, admin_user):
        import uuid

        from app.services import archive

        eid = uuid.uuid4()
        a = archive.store(db, entity_type="invoice", entity_id=eid, kind="pdf", document_number="RE-X", data=b"%PDF-eins", user_id=admin_user.id)
        b = archive.store(db, entity_type="invoice", entity_id=eid, kind="pdf", document_number="RE-X", data=b"%PDF-zwei", user_id=admin_user.id)
        assert a.id == b.id and Path(a.file_path).read_bytes() == b"%PDF-eins"


class TestHandelsbriefe:
    """Angebote und Bestellungen sind Handelsbriefe (§ 257 HGB) und werden beim Versenden archiviert."""

    def _quote(self, client, customer):
        res = client.post("/api/v1/quotes", json={"customer_id": str(customer.id), "quote_date": "2026-10-13", "items": ITEMS})
        assert res.status_code == 201, res.text
        return res.json()

    def test_angebot_versendet_bleibt_unveraendert(self, admin_client, db, sample_customer, company_settings):
        q = self._quote(admin_client, sample_customer)
        admin_client.post(f"/api/v1/quotes/{q['id']}/status", json={"status": "sent"})
        before = admin_client.get(f"/api/v1/quotes/{q['id']}/pdf").content
        _set_company(db, "Neue Firma GmbH")
        assert admin_client.get(f"/api/v1/quotes/{q['id']}/pdf").content == before
        assert "pdf" in _docs(db, q["id"])

    def test_angebot_email_archiviert_genau_die_versendete_datei(self, admin_client, db, sample_customer, company_settings, monkeypatch):
        sent = {}
        monkeypatch.setattr("app.services.email.send_email_with_attachment", lambda db, **kw: sent.update(kw))
        q = self._quote(admin_client, sample_customer)
        admin_client.post(f"/api/v1/quotes/{q['id']}/send-email", json={"recipient_email": "k@test.de"})
        assert Path(_docs(db, q["id"])["pdf"].file_path).read_bytes() == sent["attachment_data"]

    def test_bestellung_archiviert(self, admin_client, db, company_settings, monkeypatch):
        from app.models.supplier import Supplier

        sup = Supplier(name="Teile AG", email="b@teile.de")
        db.add(sup)
        db.flush()
        po = admin_client.post("/api/v1/purchase-orders", json={
            "supplier_id": str(sup.id), "order_date": "2026-10-14",
            "items": [{"description": "Schraube", "quantity": 2, "unit_price": "1.00"}]}).json()
        sent = {}
        monkeypatch.setattr("app.services.email.send_email_with_attachment", lambda db, **kw: sent.update(kw))
        admin_client.post(f"/api/v1/purchase-orders/{po['id']}/send-email", json={})
        assert Path(_docs(db, po["id"])["pdf"].file_path).read_bytes() == sent["attachment_data"]
        _set_company(db, "Neue Firma GmbH")
        assert admin_client.get(f"/api/v1/purchase-orders/{po['id']}/pdf").content == sent["attachment_data"]
