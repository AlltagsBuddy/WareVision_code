"""Rauchtest: Jede Seite lädt ohne JavaScript-Fehler und zeigt ihre Überschrift."""

import pytest

SEITEN = [
    ("/", "Willkommen"),
    ("/customers", "Kunden"),
    ("/vehicles", "Fahrzeuge"),
    ("/articles", "Artikel"),
    ("/suppliers", "Lieferanten"),
    ("/stock", "Lager"),
    ("/stock-counts", "Inventur"),
    ("/purchase-orders", "Bestellungen"),
    ("/quotes", "Angebote"),
    ("/workshop-orders", "Werkstatt"),
    ("/maintenance-plans", "Wartungspl"),
    ("/appointments", "Termin"),
    ("/invoices", "Rechnungen"),
    ("/documents", "Dokumente"),
    ("/help", "Hilfe"),
    ("/users", "Benutzer"),
    ("/accounting", "Steuerberater"),
    ("/settings", "Einstellungen"),
    ("/audit-logs", "Audit"),
]


@pytest.mark.parametrize("pfad,titel", SEITEN)
def test_seite_laedt(page, base_url, pfad, titel):
    page.goto(f"{base_url}{pfad}")
    page.wait_for_load_state("networkidle")
    h1 = page.locator("h1").first.inner_text()
    assert titel.lower() in h1.lower(), f"{pfad}: Überschrift „{h1}“"
    assert not page.js_errors, f"{pfad}: JavaScript-Fehler {page.js_errors}"


def test_navigation_enthaelt_neue_bereiche(page, base_url):
    page.goto(base_url)
    page.wait_for_selector("aside.sidebar >> text=Einstellungen")   # Admin-Bereich nach dem Laden des Benutzers
    nav = page.locator("aside.sidebar").inner_text()
    for eintrag in ("Angebote", "Bestellungen", "Inventur", "Hilfe", "Werkstattaufträge", "Wartungspläne"):
        assert eintrag in nav
    for gruppe in ("WERKSTATT", "KUNDEN", "LAGER & EINKAUF", "FINANZEN", "VERWALTUNG"):
        assert gruppe in nav.upper()


def test_seitenleiste_markiert_aktive_seite(page, base_url):
    page.goto(f"{base_url}/invoices")
    page.wait_for_selector("aside.sidebar a[aria-current='page']")
    active = page.locator("aside.sidebar a[aria-current='page']")
    assert active.count() == 1 and active.inner_text() == "Rechnungen"


def test_konto_menue(page, base_url):
    page.goto(base_url)
    page.wait_for_selector(".account-button")
    assert page.locator("text=Abmelden").count() == 0          # erst nach Klick sichtbar
    page.click(".account-button")
    menu = page.locator(".account-menu")
    for eintrag in ("Meine Daten exportieren", "Passwort ändern", "Abmelden"):
        assert eintrag in menu.inner_text()
    page.keyboard.press("Escape")
    assert page.locator(".account-menu").count() == 0


def test_mobil_menue(page, base_url):
    page.set_viewport_size({"width": 390, "height": 800})
    page.goto(base_url)
    assert not page.locator("aside.sidebar >> text=Rechnungen").is_visible() or page.locator(".nav-toggle").is_visible()
    page.click(".nav-toggle")
    page.click("aside.sidebar >> text=Rechnungen")
    page.wait_for_url("**/invoices")
    page.wait_for_timeout(300)
    box = page.locator("aside.sidebar").bounding_box()
    assert box is None or box["x"] + box["width"] <= 1    # Menü nach Klick wieder zu
