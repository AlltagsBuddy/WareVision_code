"""Fachliche Abläufe im Browser: Angebot → Werkstattauftrag, Bestellung → Wareneingang, Inventur, Hilfe."""

from datetime import date


def test_angebot_anlegen_annehmen_umwandeln(page, base_url):
    page.goto(f"{base_url}/quotes")
    page.click("text=+ Neues Angebot")
    modal = page.locator(".modal")
    modal.locator("select").nth(1).select_option(index=1)          # erster Kunde
    page.wait_for_timeout(500)
    if modal.locator("select").nth(2).locator("option").count() > 1:
        modal.locator("select").nth(2).select_option(index=1)      # Fahrzeug
    modal.locator('input[placeholder="z. B. Reparatur Bremsanlage"]').fill("E2E Inspektion")
    row = modal.locator("tbody tr").first
    row.locator("input").nth(0).fill("Arbeitszeit E2E")
    row.locator("input").nth(1).fill("1,5")
    row.locator("input").nth(3).fill("89")
    modal.locator("button[type=submit]").click()
    page.wait_for_selector("text=(Entwurf)")
    title = page.locator(".modal h2").first.inner_text()
    assert "AN-" in title
    page.click(".modal >> text=Angenommen")
    page.wait_for_selector("text=(Angenommen)")
    page.click(".modal >> text=In Werkstattauftrag umwandeln")
    convert_btn = page.locator(".modal >> text=Werkstattauftrag anlegen")
    if convert_btn.is_disabled():
        return  # Kunde ohne Fahrzeug – Umwandlung zu Recht gesperrt
    convert_btn.click()
    page.wait_for_selector("text=(In Auftrag umgewandelt)")
    assert not page.js_errors


def test_hilfe_suche_und_assistent(page, base_url):
    page.goto(f"{base_url}/help")
    page.fill("input[aria-label='Hilfe durchsuchen']", "Inventur")
    page.wait_for_timeout(600)
    assert "Inventur" in page.locator("body").inner_text()
    page.fill("input[aria-label='Frage an den Assistenten']", "Wie storniere ich eine Rechnung?")
    page.click("button:has-text('Fragen')")
    page.wait_for_selector("text=Siehe:", timeout=30000)
    assert not page.js_errors


def test_inventur_zaehlen_und_abschliessen(page, base_url):
    page.goto(f"{base_url}/stock-counts")
    if page.locator("text=Zählung läuft").count():
        page.click("text=Zählung läuft")
        page.click("text=Abbrechen")
        page.click("text=← Alle Inventuren")
    page.click("text=+ Neue Inventur")
    page.fill(".modal input[type=date]", date.today().isoformat())
    page.click("text=Inventur starten")
    page.wait_for_selector("text=Zählung läuft")
    # Blindzählung: Soll vor Eingabe verborgen
    assert page.locator("tbody tr").first.locator("td").nth(4).inner_text().strip() == "·"
    inputs = page.locator("tbody input[inputmode=numeric]")
    for i in range(inputs.count()):
        inputs.nth(i).fill("1")
        inputs.nth(i).press("Tab")
    page.wait_for_function("document.body.innerText.includes('100 %')", timeout=60000)
    page.click("text=Inventur abschließen")
    page.wait_for_selector("text=(Abgeschlossen)", timeout=60000)
    assert page.locator("tbody input[inputmode=numeric]").count() == 0
    assert not page.js_errors


def test_bestellung_anlegen_bestellen_wareneingang(page, base_url):
    page.goto(f"{base_url}/purchase-orders")
    page.click("text=+ Neue Bestellung")
    supplier = page.locator("#po-supplier")
    if supplier.locator("option").count() < 2:
        return  # kein Lieferant in der Testinstanz
    supplier.select_option(index=1)
    page.fill("input[aria-label='Bezeichnung Position 1']", "E2E Testteil")
    page.fill("input[aria-label='Menge Position 1']", "3")
    page.fill("input[aria-label='EK Position 1']", "2,50")
    page.locator(".modal button[type=submit]").click()
    page.wait_for_selector("text=(Entwurf)")
    assert "BE-" in page.locator(".modal h2").first.inner_text()
    page.click(".modal >> text=Als bestellt markieren")
    page.wait_for_selector("text=(Bestellt)")
    page.click(".modal >> button:has-text('Wareneingang')")
    page.fill("input[aria-label='Geliefert Position 1']", "2")
    page.click("text=Wareneingang buchen")
    page.wait_for_selector("text=(Teilweise geliefert)")
    page.click(".modal >> button:has-text('Wareneingang')")
    page.click("text=Wareneingang buchen")
    page.wait_for_selector("text=(Geliefert)")
    page.click(".modal >> text=Schließen")
    page.click("text=Bestellvorschlag")
    page.wait_for_timeout(500)
    assert not page.js_errors


def _api(page, base_url, method, path, data=None):
    """API-Aufruf mit dem Login der Browser-Sitzung (Token aus dem localStorage)."""
    token = page.evaluate("() => localStorage.getItem('token')")
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{base_url}/api/v1{path}"
    res = page.request.fetch(url, method=method, headers=headers, data=data)
    assert res.ok, res.text()
    return res.json()


def test_rechnungskorrektur_kulanz(page, base_url):
    page.goto(f"{base_url}/invoices")
    customers = _api(page, base_url, "GET", "/customers?limit=1")
    if not customers:
        return  # kein Kunde in der Testinstanz
    inv = _api(page, base_url, "POST", "/invoices", {
        "customer_id": customers[0]["id"], "invoice_date": date.today().isoformat(),
        "items": [{"description": "E2E Leistung", "quantity": 1, "unit_price": 50, "vat_rate": 19}],
    })
    _api(page, base_url, "POST", f"/invoices/{inv['id']}/issue")
    page.reload()
    row = page.locator("tr").filter(has=page.get_by_text(inv["invoice_number"], exact=True))
    row.locator("button:has-text('Gutschrift / Korrektur')").click()
    page.wait_for_selector("text=Gutschrift brutto")
    page.fill("#rk-discount-net", "10")
    page.fill("#rk-reason", "E2E Kulanz")
    page.click("text=Rechnungskorrektur erstellen")
    page.wait_for_selector("text=Rechnungskorrektur erstellt")
    assert "RK-" in page.locator(".modal").first.inner_text()
    page.click(".modal >> text=Schließen")
    page.wait_for_selector("text=Erstattung offen")
    row = page.locator("tr").filter(has=page.get_by_text(inv["invoice_number"], exact=True))
    assert "korrigiert durch RK-" in row.inner_text()
    assert row.locator("text=Stornieren").count() == 0  # nach Korrektur nur noch weitere Korrekturen möglich
    assert not page.js_errors


def test_datev_export_vorschau(page, base_url):
    page.goto(f"{base_url}/accounting")
    _api(page, base_url, "PUT", "/accounting/datev/settings",
         {"consultant_number": 1234567, "client_number": 56789, "chart": "SKR03"})
    page.reload()
    page.wait_for_selector("text=DATEV-Export (Buchungsstapel)")
    page.click("button:has-text('Vorschau')")
    page.wait_for_selector("text=Ausgangsrechnungen:")
    assert "Belege" in page.locator("body").inner_text()
    with page.expect_download() as dl:
        page.click("text=DATEV-Export herunterladen")
    assert dl.value.suggested_filename.startswith("DATEV_")
    assert not page.js_errors
