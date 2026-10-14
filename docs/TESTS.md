# Automatische Tests – WareVision

Stand: 14.10.2026 (mit Belegarchiv, Auftragsfotos, Wartungsplan nach Baujahr und Teile-Hersteller)

Es gibt drei Ebenen von Tests:

| Ebene | Ort | Werkzeug | Anzahl (Stand) |
|---|---|---|---|
| Backend (API, Berechnungen, PDF, E-Rechnung) | `backend/tests/` | pytest | 390 |
| Frontend (Seiten, Formulare) | `frontend/src/**/*.test.tsx` | vitest | 107 |
| Ende-zu-Ende im Browser | `e2e/` | pytest + Playwright | 36 |

---

## 1. Backend-Tests (empfohlen: im Docker-Container)

Die Tests nutzen eine **eigene Datenbank `warevision_test`** auf demselben
PostgreSQL-Server. Sie wird beim ersten Lauf automatisch angelegt.
Jeder Test läuft in einer Transaktion, die danach zurückgerollt wird.
**Die echte Datenbank `warevision` wird nie verändert** (der Testlauf bricht
ab, falls er versehentlich darauf zeigen würde).

Schritt für Schritt (PowerShell, im Ordner `D:\WareVision\WareVision_code`):

1. Container starten (falls nicht schon laufend):
   ```powershell
   docker compose up -d --build
   ```
2. Tests ausführen:
   ```powershell
   docker compose exec backend sh -c "pip install -q -r requirements-test.txt && pytest -q"
   ```
3. Ergebnis: Am Ende steht z. B. `388 passed, 2 skipped`.
   `skipped` ist die optionale Schematron-Prüfung (siehe Punkt 4).

Einzelne Bereiche testen:
```powershell
docker compose exec backend pytest -q tests/test_quotes.py
docker compose exec backend pytest -q tests/test_einvoice.py
docker compose exec backend pytest -q -k Inventur
```

### Was geprüft wird (Auszug)

| Datei | Inhalt |
|---|---|
| `test_quotes.py` | Angebote/KVA: Summen je Steuersatz, Statuswechsel, Umwandlung in Werkstattauftrag inkl. Lagerbuchung, PDF (§ 649 BGB-Hinweis), E-Mail (simuliert) |
| `test_purchase_orders.py` | Bestellwesen: Bestellvorschlag (Mindest-/Zielbestand, Reservierungen, offene Bestellungen), Summen, PDF, E-Mail, Wareneingang mit Teillieferung, Storno, Rechte |
| `test_invoice_corrections.py` | Rechnungskorrektur/Gutschrift: Teilmengen, Nachlass, Obergrenzen, Lagerrücknahme, Storno der Korrektur, keine Mahnung/Überfälligkeit, PDF mit Bezug, ZUGFeRD (XSD + optional Schematron), Steuerberater-Export |
| `test_datev.py` | DATEV-Export: Kopfzeile EXTF 700/Formatversion 13 (31 Felder), 125 Spalten, Windows-1252, CR/LF, Buchungen je Steuersatz (Summe = Rechnungsbrutto), Storno/Korrektur im Haben, Eingangsrechnungen und Lieferanten-Gutschriften, Belegfeld-Bereinigung, dauerhafte Debitoren/Kreditoren, Stammdatei (254 Felder), Wirtschaftsjahr, Einstellungen |
| `test_archive.py` | Belegarchiv (GoBD): Original beim Ausstellen (PDF + ZUGFeRD), unverändert trotz späterer Firmen-/Kundenänderung und DSGVO-Anonymisierung, Manipulation/fehlende Datei erkannt, E-Mail und Steuerberater-Export nutzen Original, Mahnbriefe, Storno/Korrektur, Angebote/Bestellungen, Nachziehen, nie überschreiben |
| `test_werkstatt_erweiterungen.py` | Wartungsplan nach Baujahr (Vorrang Modell/Baujahr, unbekanntes Baujahr), Teile-Hersteller und Suche, passende Artikel je Modell, Auftragsfotos (Upload, Dateityp-Prüfung, Zugriff, Löschen, DSGVO), Suche Eingangsrechnungen/Audit-Log, Storno → Auftrag korrigieren → neue Rechnung inkl. Lager |
| `test_stock_counts.py` | Inventur: Blindzählung, Buchungen während der Zählung, Differenzbuchung, CSV/PDF |
| `test_einvoice.py` | Rechnungen: Pflichtangaben § 14 UStG, MwSt je Satz, Storno, ZUGFeRD EN16931 (XSD-Prüfung), PDF/A-3, eingebettete Schriften; Eingangsrechnungen ZUGFeRD/XRechnung (UBL + CII), Dubletten, GoBD-Archiv |
| `test_stammdaten.py` | Lieferanten, Lagerorte, Kategorien, Stundensätze, Hersteller, Barcode, Reservierungen |
| `test_verwaltung.py` | Benutzer & Rechte, Registrierung (inaktiv bis Freischaltung), DSGVO-Export, Audit-Log, Steuerberater-Export, Einstellungen, Terminmarktplatz-Webhook |
| `test_help.py` | Hilfe-Center, Suche, KI-Assistent (Claude wird simuliert – es wird **nichts** an Anthropic gesendet), Entfernen personenbezogener Daten |

### 4. Optional: Schematron-Prüfung EN16931

Die offizielle EN16931-Schematron-Prüfung läuft nur, wenn die XSLT-Datei
vorhanden ist und `saxonche` installiert ist:
```powershell
docker compose exec backend pip install saxonche
docker compose exec -e EN16931_CII_XSLT=/pfad/EN16931-CII-validation.xslt backend pytest -q tests/test_einvoice.py
```
Die XSLT-Datei gibt es im Release-Paket von
`ConnectingEurope/eInvoicing-EN16931` (GitHub).

---

## 2. Frontend-Tests

Im Ordner `frontend` (Node.js nötig, `npm install` einmalig):
```powershell
cd frontend
npm test
```
Typprüfung zusätzlich:
```powershell
npx tsc --noEmit -p tsconfig.json
```
Die API wird in diesen Tests simuliert – es wird kein Backend benötigt.

---

## 3. Ende-zu-Ende-Tests (Browser)

**Wichtig:** Diese Tests legen echte Datensätze an (Angebote, Inventuren).
Deshalb laufen sie **nur**, wenn zwei Umgebungsvariablen gesetzt sind.
Nur gegen eine **Testinstanz** ausführen, nie gegen die echte Firmendatenbank!

1. Einmalig installieren:
   ```powershell
   pip install pytest playwright
   playwright install chromium
   ```
2. Ausführen:
   ```powershell
   $env:E2E_BASE_URL = "http://localhost:5173"
   $env:E2E_ALLOW_WRITE = "1"
   $env:E2E_USER = "admin@test.de"         # Admin-Zugang der TESTinstanz
   $env:E2E_PASSWORD = "..."
   pytest -q e2e
   ```
Ohne diese Variablen werden die Tests übersprungen (`skipped`).

---

## Wann laufen lassen?

- Nach jeder Änderung am Code, **vor** dem Commit.
- Nach einem Update von Python-/Node-Paketen.
- Schlägt ein Test fehl: Meldung lesen, Fehler beheben, nicht den Test „passend machen“.
