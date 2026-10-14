"""Tests: Hilfe-Center, Stichwortsuche und KI-Assistent (Claude-API wird simuliert)."""

import json

import pytest

from app.services import help_assistant as ha

V1 = "/api/v1/help"


@pytest.fixture()
def fake_claude(monkeypatch):
    """Simuliert die Anthropic Messages API und merkt sich die Anfragen."""
    calls: list[dict] = []
    state = {"answer": "1. Öffne **Rechnungen**.\n2. Klicke auf „Stornieren“.\nQuellen: [Quelle: rechnungen--stornieren]",
             "error": None}

    class FakeResponse:
        def __init__(self, data):
            self._data = data

        def read(self):
            return json.dumps(self._data).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=None):
        body = json.loads(req.data.decode())
        calls.append({"url": req.full_url, "headers": dict(req.header_items()), "body": body})
        if state["error"]:
            raise state["error"]
        return FakeResponse({"content": [{"type": "text", "text": state["answer"]}]})

    monkeypatch.setattr(ha.urllib.request, "urlopen", fake_urlopen)
    return {"calls": calls, "state": state}


@pytest.fixture()
def ai_key(db):
    from app.models.app_setting import AppSetting
    db.add(AppSetting(key="ai_help_api_key", value="sk-ant-test"))
    db.flush()


class TestWissensbasis:
    def test_alle_module_beschrieben(self):
        titles = " ".join(a.title for a in ha.load_articles())
        for module in ("Kunden", "Fahrzeuge", "Artikel", "Lieferanten", "Lager", "Bestellungen", "Inventur", "Angebote",
                       "Werkstattaufträge", "Wartungspläne", "Terminplaner", "Rechnungen", "Buchhaltung",
                       "Dokumente", "Einstellungen", "Benutzer"):
            assert module in titles, f"Hilfe zu „{module}“ fehlt"

    def test_abschnitte_eindeutig_und_nicht_leer(self):
        ids = [s.id for s in ha.all_sections()]
        assert len(ids) == len(set(ids))
        assert all(s.text.strip() for s in ha.all_sections())

    def test_api_artikel(self, admin_client):
        data = admin_client.get(f"{V1}/articles").json()
        assert len(data) >= 15
        assert all(a["sections"] for a in data)

    def test_ohne_login(self, client):
        assert client.get(f"{V1}/articles").status_code == 401


class TestSuche:
    @pytest.mark.parametrize("frage,kapitel", [
        ("Wie storniere ich eine Rechnung?", "rechnungen"),
        ("Wie wandle ich ein Angebot in einen Werkstattauftrag um?", "angebote"),
        ("Wie schließe ich die Inventur ab?", "inventur"),
        ("E-Rechnung XRechnung importieren", "buchhaltung"),
        ("Wo trage ich die IBAN ein?", "einstellungen"),
        ("Leistungsdatum auf der Rechnung", "rechnungen"),
        ("Barcode scannen im Lager", "lager"),
        ("Wie buche ich den Wareneingang einer Bestellung?", "bestellungen"),
        ("Was muss ich nachbestellen?", "bestellungen"),
        ("Wie erstelle ich eine Gutschrift für eine bezahlte Rechnung?", "rechnungen"),
        ("Kunde hat ein Teil zurückgegeben, Teilgutschrift", "rechnungen"),
        ("Wie lange muss ich Rechnungen aufbewahren?", "recht_und_fristen"),
    ])
    def test_relevanter_treffer(self, frage, kapitel):
        hits = ha.search(frage)
        assert hits, f"Kein Treffer für: {frage}"
        assert kapitel in [h.article_id for h in hits[:3]], f"{frage} → {[h.id for h in hits]}"

    def test_api_suche(self, admin_client):
        res = admin_client.get(f"{V1}/search?q=Stornorechnung")
        assert res.status_code == 200 and res.json()

    def test_ohne_treffer(self, admin_client):
        res = admin_client.post(f"{V1}/ask", json={"question": "Xylophon Quantenschaum"})
        assert res.json()["mode"] == "search"
        assert "nichts gefunden" in res.json()["answer"]


class TestDatenschutz:
    @pytest.mark.parametrize("text,erwartet", [
        ("Mail an max@test.de", "[E-Mail entfernt]"),
        ("IBAN DE02 1203 0000 0000 2020 51", "[IBAN entfernt]"),
        ("Ruf 0951 123456 an", "[Telefon entfernt]"),
        ("Quad BA-QP 123", "[Kennzeichen entfernt]"),
    ])
    def test_personenbezogenes_entfernt(self, text, erwartet):
        clean, changed = ha.redact(text)
        assert changed and erwartet in clean

    def test_normaler_text_bleibt(self):
        clean, changed = ha.redact("Wie storniere ich die Rechnung RE-2026-0001?")
        assert not changed and "RE-2026-0001" in clean


class TestKiAssistent:
    def test_status_ohne_schluessel(self, admin_client):
        assert admin_client.get(f"{V1}/status").json()["ai_enabled"] is False

    def test_ohne_schluessel_stichwortsuche(self, admin_client, fake_claude):
        res = admin_client.post(f"{V1}/ask", json={"question": "Wie storniere ich eine Rechnung?"}).json()
        assert res["mode"] == "search"
        assert res["sources"]
        assert fake_claude["calls"] == []  # nichts verlässt den Server

    def test_mit_schluessel_ki_antwort(self, admin_client, ai_key, fake_claude):
        res = admin_client.post(f"{V1}/ask", json={"question": "Wie storniere ich eine Rechnung?"}).json()
        assert res["mode"] == "ai"
        assert "Stornieren" in res["answer"]
        assert "Quelle" not in res["answer"]  # technische Kennungen entfernt
        assert res["sources"][0]["id"] == "rechnungen--stornieren"
        call = fake_claude["calls"][0]
        assert call["headers"]["X-api-key"] == "sk-ant-test"
        assert call["body"]["model"] == ha.DEFAULT_MODEL
        assert "ANLEITUNG" in call["body"]["system"]
        assert call["body"]["messages"][-1] == {"role": "user", "content": "Wie storniere ich eine Rechnung?"}

    def test_personenbezug_wird_nicht_gesendet(self, admin_client, ai_key, fake_claude):
        res = admin_client.post(f"{V1}/ask", json={"question": "Kunde max@test.de hat Kennzeichen BA-QP 123, was tun?"}).json()
        sent = json.dumps(fake_claude["calls"][0]["body"]["messages"])
        assert "max@test.de" not in sent and "BA-QP 123" not in sent
        assert res["notice"] and "entfernt" in res["notice"]

    def test_verlauf_wird_bereinigt(self, admin_client, ai_key, fake_claude):
        history = [
            {"role": "assistant", "content": "Hallo!"},          # darf nicht am Anfang stehen
            {"role": "user", "content": "Frage 1"},
            {"role": "user", "content": "Frage 1b"},              # doppelte Rolle
            {"role": "assistant", "content": "Antwort 1"},
        ]
        admin_client.post(f"{V1}/ask", json={"question": "Frage 2", "history": history})
        roles = [m["role"] for m in fake_claude["calls"][0]["body"]["messages"]]
        assert roles[0] == "user"
        assert all(a != b for a, b in zip(roles, roles[1:]))
        assert roles[-1] == "user"

    @pytest.mark.parametrize("status,text", [(401, "ungültig"), (429, "ausgelastet"), (500, "nicht erreichbar")])
    def test_fehler_fallback_auf_suche(self, admin_client, ai_key, fake_claude, status, text):
        import urllib.error
        fake_claude["state"]["error"] = urllib.error.HTTPError("u", status, "x", {}, None)
        res = admin_client.post(f"{V1}/ask", json={"question": "Wie storniere ich eine Rechnung?"}).json()
        assert res["mode"] == "search"
        assert text in res["notice"]
        assert res["sources"]

    def test_netzwerkfehler_fallback(self, admin_client, ai_key, fake_claude):
        import urllib.error
        fake_claude["state"]["error"] = urllib.error.URLError("offline")
        res = admin_client.post(f"{V1}/ask", json={"question": "Inventur abschließen"}).json()
        assert res["mode"] == "search"

    def test_nutzung_protokolliert_ohne_inhalt(self, admin_client, db, ai_key, fake_claude):
        from app.models.audit_log import AuditLog
        admin_client.post(f"{V1}/ask", json={"question": "Geheime Frage zur Inventur"})
        log = db.query(AuditLog).filter(AuditLog.entity_type == "help").first()
        assert log is not None and log.action == "ai_question"
        assert "Geheime" not in json.dumps(log.new_values or {})

    def test_frage_zu_kurz_zu_lang(self, admin_client):
        assert admin_client.post(f"{V1}/ask", json={"question": "a"}).status_code == 422
        assert admin_client.post(f"{V1}/ask", json={"question": "x" * 1001}).status_code == 422
