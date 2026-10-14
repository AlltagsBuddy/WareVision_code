"""End-to-End-Tests mit echtem Browser (Playwright) gegen eine laufende WareVision-Instanz.

ACHTUNG: Die Tests legen Daten an (Angebote, Inventur, Rechnungen). Nur gegen eine
TEST-Instanz laufen lassen, niemals gegen den Echtbetrieb der Werkstatt!

Start:
    set E2E_BASE_URL=http://localhost:5173
    set E2E_ALLOW_WRITE=1
    pytest e2e
Optional: E2E_USER / E2E_PASSWORD (Standard: admin@warevision.local / admin123)
"""

import os

import pytest

BASE_URL = os.getenv("E2E_BASE_URL", "").rstrip("/")
USER = os.getenv("E2E_USER", "admin@warevision.local")
PASSWORD = os.getenv("E2E_PASSWORD", "admin123")


def pytest_collection_modifyitems(config, items):
    """Ohne ausdrückliche Freigabe werden die E2E-Tests übersprungen (Schutz vor Echtdaten)."""
    if not BASE_URL or os.getenv("E2E_ALLOW_WRITE") != "1":
        skip = pytest.mark.skip(reason="E2E_BASE_URL und E2E_ALLOW_WRITE=1 setzen (nur Testinstanz!)")
        for item in items:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture(scope="session")
def auth_state(browser):
    """Einmal anmelden und die Sitzung wiederverwenden (der Login ist pro Minute begrenzt)."""
    context = browser.new_context()
    pg = context.new_page()
    pg.goto(f"{BASE_URL}/login")
    pg.fill("input[type=text]", USER)
    pg.fill("input[type=password]", PASSWORD)
    pg.click("button[type=submit]")
    pg.wait_for_url(lambda url: "/login" not in url, timeout=10000)
    state = context.storage_state()
    context.close()
    return state


@pytest.fixture()
def page(browser, auth_state):
    """Angemeldete Browserseite; sammelt JavaScript-Fehler in page.js_errors."""
    context = browser.new_context(viewport={"width": 1400, "height": 1000}, locale="de-DE", storage_state=auth_state)
    pg = context.new_page()
    pg.js_errors = []
    pg.on("pageerror", lambda e: pg.js_errors.append(str(e)))
    pg.on("console", lambda m: pg.js_errors.append(m.text) if m.type == "error" else None)
    pg.on("dialog", lambda d: d.accept())
    yield pg
    context.close()


@pytest.fixture()
def base_url():
    return BASE_URL
