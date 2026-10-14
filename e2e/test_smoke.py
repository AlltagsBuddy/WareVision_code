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
    nav = page.locator("nav").inner_text()
    for eintrag in ("Angebote", "Inventur", "Hilfe"):
        assert eintrag in nav
