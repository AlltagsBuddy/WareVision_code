"""Browser: Fotos am Auftrag, Wartungsplan mit Baujahr, Suchfelder, passende Teile."""

import struct
import zlib


def _png() -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0)
    raw = b"\x00" + b"\xff\x00\x00" * 2 + b"\x00" + b"\x00\x00\xff" * 2
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def test_foto_am_auftrag(page, base_url, tmp_path):
    page.goto(f"{base_url}/workshop-orders")
    page.wait_for_selector("tbody tr")
    page.locator("tbody tr").first.click()
    page.wait_for_selector("text=Fotos")
    before = page.locator(".order-photo-thumb").count()
    foto = tmp_path / "e2e_foto.png"
    foto.write_bytes(_png())
    page.set_input_files("[data-testid=photo-file-input]", str(foto))
    page.wait_for_function(f"document.querySelectorAll('.order-photo-thumb img').length > {before}")
    page.locator(".order-photo-thumb").last.click()
    page.fill("#photo-caption", "E2E Testfoto")
    page.click("text=Beschreibung speichern")
    page.wait_for_selector(".order-photo-thumb >> text=E2E Testfoto")
    page.once("dialog", lambda d: d.accept())
    page.click("text=Foto entfernen")
    page.wait_for_function(f"document.querySelectorAll('.order-photo-thumb').length === {before}")
    assert not page.js_errors


def test_wartungsplan_mit_baujahr(page, base_url):
    page.goto(f"{base_url}/maintenance-plans")
    page.click("text=+ Neuer Wartungsplan")
    modal = page.locator(".modal")
    modal.locator("select").first.select_option(index=1)
    modal.locator("input").filter(has_not=page.locator("[type=number]")).first.fill("E2E Altfahrzeuge")
    page.fill("#mp-year-to", "2012")
    modal.locator("button[type=submit]").click()
    page.fill("input[placeholder='Name, Hersteller, Modell...']", "E2E Altfahrzeuge")
    row = page.locator("tbody tr", has_text="E2E Altfahrzeuge").first
    assert "bis 2012" in row.inner_text()
    assert not page.js_errors


def test_suchfelder(page, base_url):
    page.goto(f"{base_url}/appointments")
    page.fill("input[aria-label='Termine suchen']", "zz-kein-treffer-e2e")
    page.wait_for_selector("text=0 Termin(e) gefunden")
    page.goto(f"{base_url}/audit-logs")
    page.fill("input[aria-label='Audit-Log durchsuchen']", "zz-kein-treffer-e2e")
    page.wait_for_selector("text=Keine Einträge vorhanden.")
    page.goto(f"{base_url}/users")
    page.fill("input[aria-label='Benutzer suchen']", "zz-kein-treffer-e2e")
    page.wait_for_selector("text=Keine Benutzer gefunden.")
    assert not page.js_errors


def test_passende_teile_filter(page, base_url):
    page.goto(f"{base_url}/articles")
    select = page.locator("select[aria-label='Passend für Fahrzeugmodell']")
    select.wait_for()
    options = select.locator("option")
    if options.count() < 2:
        return  # keine Fahrzeugmodelle in der Testinstanz
    value = options.nth(1).get_attribute("value")
    select.select_option(value)
    page.wait_for_url(f"**/articles?modell={value}")
    assert not page.js_errors
