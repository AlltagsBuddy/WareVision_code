"""Tests: DATEV-Export (Buchungsstapel EXTF 700 / Formatversion 13, Personenkonten, Einstellungen)."""

import io
import zipfile
from decimal import Decimal

import pytest

A = "/api/v1/accounting/datev"
INV = "/api/v1/invoices"

SETTINGS = {"consultant_number": 1234567, "client_number": 56789, "chart": "SKR03"}

MIXED = [
    {"description": "Arbeit", "quantity": 1.5, "unit": "Std.", "unit_price": 89, "vat_rate": 19},
    {"description": "Fachbuch", "quantity": 1, "unit": "Stk", "unit_price": 24.99, "vat_rate": 7},
    {"description": "TÜV-Gebühr", "quantity": 1, "unit": "Stk", "unit_price": 98.5, "vat_rate": 0},
]


@pytest.fixture()
def datev_ready(admin_client):
    res = admin_client.put(f"{A}/settings", json=SETTINGS)
    assert res.status_code == 200, res.text
    assert res.json()["problems"] == []
    return res.json()


def _invoice(client, customer, items=MIXED, date="2026-10-13", service_date="2026-10-10", issue=True):
    res = client.post(INV, json={"customer_id": str(customer.id), "invoice_date": date, "service_date": service_date,
                                 "due_date": "2026-10-27", "items": items})
    assert res.status_code == 201, res.text
    inv = res.json()
    if issue:
        assert client.post(f"{INV}/{inv['id']}/issue").status_code == 200
    return inv


def _export(client, date_from="2026-10-01", date_to="2026-10-31", **params):
    res = client.get(f"{A}/export", params={"date_from": date_from, "date_to": date_to, **params})
    assert res.status_code == 200, res.text
    return zipfile.ZipFile(io.BytesIO(res.content))


def _read(z, prefix):
    name = next(n for n in z.namelist() if n.startswith(prefix))
    raw = z.read(name)
    return raw, raw.decode("cp1252").split("\r\n")


def _fields(line):
    """Semikolon-Felder (Anführungszeichen entfernt)."""
    import csv
    return next(csv.reader([line], delimiter=";", quotechar='"'))


class TestEinstellungen:
    def test_vorschlaege_skr03_und_skr04(self, admin_client):
        s = admin_client.get(f"{A}/settings").json()
        assert s["revenue_19"] == "8400" and s["revenue_7"] == "8300" and s["expense_19"] == "3400"
        assert any("Beraternummer" in p for p in s["problems"])
        s = admin_client.put(f"{A}/settings", json={**SETTINGS, "chart": "SKR04"}).json()
        assert s["revenue_19"] == "4400" and s["expense_19"] == "5400" and s["revenue_0"] == "1370"

    def test_eigene_konten_und_validierung(self, admin_client):
        s = admin_client.put(f"{A}/settings", json={**SETTINGS, "revenue_19": "8401"}).json()
        assert s["revenue_19"] == "8401"
        assert admin_client.put(f"{A}/settings", json={**SETTINGS, "revenue_19": "84A0"}).status_code == 400
        assert admin_client.put(f"{A}/settings", json={**SETTINGS, "consultant_number": 999}).status_code == 422
        s = admin_client.put(f"{A}/settings", json={**SETTINGS, "revenue_19": "840"}).json()
        assert any("4 Stellen" in p for p in s["problems"])

    def test_laengere_sachkonten_brauchen_eigene_konten(self, admin_client):
        s = admin_client.put(f"{A}/settings", json={**SETTINGS, "account_length": 5}).json()
        assert s["revenue_19"] == "" and s["problems"]
        assert s["debtor_start"] == 100000 and s["creditor_start"] == 700000

    def test_nur_admin(self, werkstatt_client):
        assert werkstatt_client.get(f"{A}/settings").status_code == 403
        assert werkstatt_client.get(f"{A}/export?date_from=2026-10-01&date_to=2026-10-31").status_code == 403

    def test_export_ohne_einstellungen_abgelehnt(self, admin_client):
        res = admin_client.get(f"{A}/export?date_from=2026-10-01&date_to=2026-10-31")
        assert res.status_code == 400 and "Beraternummer" in res.json()["detail"]


class TestBuchungsstapel:
    def test_kopfzeile_und_format(self, admin_client, b2b_customer, datev_ready):
        _invoice(admin_client, b2b_customer)
        z = _export(admin_client)
        raw, lines = _read(z, "EXTF_Buchungsstapel_Ausgang")
        assert raw.endswith(b"\r\n") and b"\r\n" in raw
        head = _fields(lines[0])
        assert len(head) == 31
        assert head[0:5] == ["EXTF", "700", "21", "Buchungsstapel", "13"]
        assert len(head[5]) == 17 and head[5].isdigit()        # erzeugt am
        assert head[10:16] == ["1234567", "56789", "20260101", "4", "20261001", "20261031"]
        assert head[18] == "1" and head[20] == "0" and head[21] == "EUR" and head[26] == "03"
        cols = _fields(lines[1])
        assert len(cols) == 125 and cols[0] == "Umsatz (ohne Soll/Haben-Kz)" and cols[124] == "Abw. Skontokonto"
        assert all(len(_fields(line)) == 125 for line in lines[2:] if line)

    def test_je_steuersatz_eine_buchung_mit_brutto(self, admin_client, b2b_customer, datev_ready):
        inv = _invoice(admin_client, b2b_customer)
        _, lines = _read(_export(admin_client), "EXTF_Buchungsstapel_Ausgang")
        rows = [_fields(line) for line in lines[2:] if line]
        assert len(rows) == 3
        by_account = {r[7]: r for r in rows}
        # 19 %: 133,50 + 25,37 = 158,87 · 7 %: 24,99 + 1,75 = 26,74 · 0 %: 98,50
        assert by_account["8400"][0] == "158,87"
        assert by_account["8300"][0] == "26,74"
        assert by_account["1590"][0] == "98,50"
        total = sum(Decimal(r[0].replace(",", ".")) for r in rows)
        assert total == Decimal(inv["gross_amount"])             # Summe = Rechnungsbrutto
        r = by_account["8400"]
        assert r[1] == "S" and r[2] == "EUR" and r[6] == "10000"   # Debitor
        assert r[8] == ""                                         # kein BU-Schlüssel (Automatikkonto)
        assert r[9] == "1310" and r[10] == inv["invoice_number"]
        assert r[113] == "0" and r[114] == "10102026" and r[116] == "27102026"
        assert "Teile Händler GmbH" in r[13]

    def test_storno_im_haben_mit_bezug(self, admin_client, b2b_customer, datev_ready):
        inv = _invoice(admin_client, b2b_customer, items=MIXED[:1])
        admin_client.post(f"{INV}/{inv['id']}/cancel", json={"reason": "Test"})
        _, lines = _read(_export(admin_client), "EXTF_Buchungsstapel_Ausgang")
        rows = [_fields(line) for line in lines[2:] if line]
        assert [r[1] for r in rows] == ["S", "H"]
        storno = rows[1]
        assert storno[0] == rows[0][0] and storno[10].startswith("STO-")
        assert f"Storno zu {inv['invoice_number']}" in storno[13]
        assert storno[116] == ""                                  # keine Fälligkeit

    def test_rechnungskorrektur_im_haben(self, admin_client, b2b_customer, datev_ready):
        inv = _invoice(admin_client, b2b_customer, items=MIXED[:1])
        admin_client.post(f"{INV}/{inv['id']}/correction", json={
            "reason": "Kulanz", "free_lines": [{"description": "Nachlass", "net_amount": "10.00", "vat_rate": 19}]})
        _, lines = _read(_export(admin_client), "EXTF_Buchungsstapel_Ausgang")
        rk = next(_fields(line) for line in lines[2:] if line and "RK-" in line)
        assert rk[0] == "11,90" and rk[1] == "H" and rk[7] == "8400"

    def test_entwuerfe_nicht_exportiert(self, admin_client, b2b_customer, datev_ready):
        _invoice(admin_client, b2b_customer, issue=False)
        z = _export(admin_client)
        assert not [n for n in z.namelist() if n.startswith("EXTF_Buchungsstapel_Ausgang")]

    def test_debitor_bleibt_gleich(self, admin_client, b2b_customer, sample_customer, datev_ready):
        _invoice(admin_client, b2b_customer)
        _invoice(admin_client, sample_customer)
        _export(admin_client)
        first = {a["name"]: a["account_number"] for a in admin_client.get(f"{A}/accounts").json()}
        assert sorted(first.values()) == [10000, 10001]
        _invoice(admin_client, sample_customer, date="2026-10-20")
        _export(admin_client)
        second = {a["name"]: a["account_number"] for a in admin_client.get(f"{A}/accounts").json()}
        assert second == first                                     # dauerhaft gleiche Nummern

    def test_vorschau_speichert_nichts(self, admin_client, b2b_customer, datev_ready):
        _invoice(admin_client, b2b_customer)
        p = admin_client.get(f"{A}/preview", params={"date_from": "2026-10-01", "date_to": "2026-10-31"}).json()
        assert p["outgoing_documents"] == 1 and p["outgoing_bookings"] == 3 and p["new_accounts"] == 1
        assert Decimal(p["outgoing_debit"]) == Decimal("284.11")
        assert admin_client.get(f"{A}/accounts").json() == []

    def test_nur_ein_wirtschaftsjahr(self, admin_client, datev_ready):
        res = admin_client.get(f"{A}/preview", params={"date_from": "2026-12-01", "date_to": "2027-01-31"})
        assert res.status_code == 400 and "31.12.2026" in res.json()["detail"]

    def test_abweichendes_wirtschaftsjahr(self, admin_client, b2b_customer):
        admin_client.put(f"{A}/settings", json={**SETTINGS, "fiscal_year_start_month": 7})
        _invoice(admin_client, b2b_customer)
        _, lines = _read(_export(admin_client), "EXTF_Buchungsstapel_Ausgang")
        assert _fields(lines[0])[12] == "20260701"

    def test_unbekannter_steuersatz_als_hinweis(self, admin_client, b2b_customer, datev_ready):
        _invoice(admin_client, b2b_customer, items=[{"description": "X", "quantity": 1, "unit_price": 10, "vat_rate": 16}])
        p = admin_client.get(f"{A}/preview", params={"date_from": "2026-10-01", "date_to": "2026-10-31"}).json()
        assert p["outgoing_documents"] == 0 and "16 %" in p["hints"][0]
        z = _export(admin_client)
        assert "16 %" in z.read("LIESMICH.txt").decode("utf-8")

    def test_umlaute_in_windows_1252(self, admin_client, db, b2b_customer, datev_ready):
        b2b_customer.company_name = 'Müller & Söhne "Quad" GmbH'
        db.flush()
        _invoice(admin_client, b2b_customer, items=MIXED[:1])
        raw, lines = _read(_export(admin_client), "EXTF_Buchungsstapel_Ausgang")
        assert "Müller & Söhne".encode("cp1252") in raw
        assert '""Quad""' in lines[2]                              # Anführungszeichen verdoppelt
        assert _fields(lines[2])[13].startswith('Müller & Söhne "Quad"')


class TestEingangsrechnungen:
    def _incoming(self, client, **extra):
        body = {"supplier_name": "Moto Teile AG", "invoice_number": "ER-77", "invoice_date": "2026-10-05",
                "net_amount": "100.00", "vat_rate": "19", **extra}
        res = client.post("/api/v1/incoming-invoices", json=body)
        assert res.status_code == 201, res.text
        return res.json()

    def test_kreditor_im_haben(self, admin_client, datev_ready):
        self._incoming(admin_client)
        _, lines = _read(_export(admin_client), "EXTF_Buchungsstapel_Eingang")
        r = _fields(lines[2])
        assert r[0] == "119,00" and r[1] == "H" and r[6] == "70000" and r[7] == "3400"
        assert r[9] == "0510" and r[10] == "ER-77"

    def test_gutschrift_lieferant_im_soll(self, admin_client, datev_ready):
        self._incoming(admin_client, is_credit_note=True, invoice_number="GS-1")
        _, lines = _read(_export(admin_client), "EXTF_Buchungsstapel_Eingang")
        r = _fields(lines[2])
        assert r[1] == "S" and r[13].startswith("Gutschrift")

    def test_belegnummer_bereinigt(self, admin_client, datev_ready):
        self._incoming(admin_client, invoice_number="2026_10.5#A")
        _, lines = _read(_export(admin_client), "EXTF_Buchungsstapel_Eingang")
        r = _fields(lines[2])
        assert r[10] == "2026-10-5-A" and "2026_10.5#A" in r[13]

    def test_gleicher_lieferant_gleicher_kreditor(self, admin_client, datev_ready):
        self._incoming(admin_client)
        self._incoming(admin_client, supplier_name="  moto teile ag ", invoice_number="ER-78")
        _, lines = _read(_export(admin_client), "EXTF_Buchungsstapel_Eingang")
        assert {_fields(line)[6] for line in lines[2:] if line} == {"70000"}

    def test_ohne_eingangsrechnungen(self, admin_client, datev_ready):
        self._incoming(admin_client)
        z = _export(admin_client, include_incoming="false")
        assert not [n for n in z.namelist() if "Eingang" in n]

    def test_unstimmige_betraege_nicht_exportiert(self, admin_client, db, datev_ready):
        from app.models.incoming_invoice import IncomingInvoice

        inv = self._incoming(admin_client)
        row = db.query(IncomingInvoice).filter(IncomingInvoice.id == inv["id"]).one()
        row.vat_amount = Decimal("12.00")   # z. B. gemischte Steuersätze
        row.gross_amount = Decimal("112.00")
        db.flush()
        p = admin_client.get(f"{A}/preview", params={"date_from": "2026-10-01", "date_to": "2026-10-31"}).json()
        assert p["incoming_bookings"] == 0 and "manuell" in p["hints"][0]


class TestPersonenkonten:
    def test_stammdaten_datei(self, admin_client, b2b_customer, sample_customer, datev_ready):
        _invoice(admin_client, b2b_customer)
        _invoice(admin_client, sample_customer)
        admin_client.post("/api/v1/incoming-invoices", json={
            "supplier_name": "Moto Teile AG", "invoice_number": "ER-1", "invoice_date": "2026-10-05", "net_amount": "10", "vat_rate": "19"})
        raw, lines = _read(_export(admin_client), "EXTF_Debitoren_Kreditoren")
        head = _fields(lines[0])
        assert head[0:5] == ["EXTF", "700", "16", "Debitoren/Kreditoren", "5"] and len(head) == 31
        assert len(_fields(lines[1])) == 254
        rows = {r[0]: r for r in (_fields(line) for line in lines[2:] if line)}
        haendler = rows["10000"]
        assert haendler[1] == "Teile Händler GmbH" and haendler[6] == "2"
        assert haendler[8] == "DE" and haendler[9] == "987654321"
        assert haendler[15] == "Industriestraße 5" and haendler[17] == "96050" and haendler[18] == "Bamberg"
        privat = rows["10001"]
        assert privat[6] == "1" and privat[3]                       # natürliche Person mit Nachname
        assert rows["70000"][1] == "Moto Teile AG"

    def test_audit(self, admin_client, db, b2b_customer, datev_ready):
        from app.models.audit_log import AuditLog

        _invoice(admin_client, b2b_customer)
        _export(admin_client)
        assert db.query(AuditLog).filter(AuditLog.action == "datev_export").count() == 1
