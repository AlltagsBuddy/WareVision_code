# WareVision – Projektkontext für Claude Code

## Sprache
- Antworte immer auf Deutsch
- Kommentare im Code auf Deutsch
- Commit-Messages auf Deutsch
- Fehlermeldungen und API-Responses auf Deutsch

---

## Projektbeschreibung
WareVision ist ein webbasiertes Warenwirtschafts- und Werkstattsystem für
**Quad Paradies Schoner** (Deutschland).

Betrieb: 1 Geschäftsführer, 1 Geschäftsführerin, 1 Mechaniker
Infrastruktur: Hetzner Server (Nürnberg), selbst gehostet

---

## Techstack

### Backend
- Python 3.12
- FastAPI
- SQLAlchemy (ORM)
- Alembic (Migrationen)
- PostgreSQL
- Pydantic v2 (Schemas)

### Frontend
- React 18 + TypeScript
- Vite
- Kein UI-Framework (eigenes CSS in App.css)

### Infrastruktur
- Docker + Docker Compose
- Nginx (Reverse Proxy)
- Hetzner Cloud (CPX31)

---

## Projektstruktur

```
WareVision_code/
├── backend/
│   ├── app/
│   │   ├── api/v1/        # API-Endpunkte (je Modul eine Datei)
│   │   ├── models/        # SQLAlchemy-Modelle
│   │   ├── schemas/       # Pydantic-Schemas
│   │   ├── services/      # Business-Logik
│   │   └── core/          # Config, DB, Security
│   ├── alembic/           # Datenbank-Migrationen
│   └── scripts/           # Init- und Seed-Skripte
├── frontend/
│   └── src/
│       ├── api/client.ts  # Alle API-Aufrufe
│       ├── pages/         # Eine Datei pro Seite
│       └── components/    # Wiederverwendbare Komponenten
├── infra/                 # Backup-Skripte
└── docs/                  # Dokumentation
```

---

## Module (bereits implementiert)

| Modul | Backend | Frontend |
|---|---|---|
| Auth / Login | ✅ | ✅ |
| Kundenverwaltung | ✅ | ✅ |
| Fahrzeugverwaltung | ✅ | ✅ |
| Artikelverwaltung | ✅ | ✅ |
| Lagerverwaltung | ✅ | ✅ |
| Werkstattaufträge | ✅ | ✅ |
| Wartungspläne | ✅ | ✅ |
| Terminplaner | ✅ | ✅ |
| Rechnungen (PDF) | ✅ | ✅ |
| Rechnungskorrektur / Gutschrift (RK-…, Teilmengen, Nachlass, Lagerrücknahme) | ✅ | ✅ |
| DATEV-Export (Buchungsstapel EXTF 700/v13, Debitoren/Kreditoren, SKR03/04) | ✅ | ✅ |
| Belegarchiv GoBD (Originale mit SHA-256, Nachziehen, Prüfung; Backup inkl. Dateien) | ✅ | ✅ |
| Fotos am Werkstattauftrag (Upload/Kamera, Beschreibung, Audit-Log, Löschen bei DSGVO-Anonymisierung) | ✅ | ✅ |
| Wartungsplan mit Baujahr von/bis (automatische Auswahl Modell > Hersteller, Baujahr > alle) | ✅ | ✅ |
| Artikel: Teile-Hersteller, Suche OEM/Lief.-Nr., Filter „passend für Modell“, „Passende Teile“ am Fahrzeug | ✅ | ✅ |
| Suche in Terminen, Benutzern, Audit-Log und Buchhaltung | ✅ | ✅ |
| Zwei-Faktor-Anmeldung (TOTP, Wiederherstellungscodes, Admin-Reset; Pflicht auf dem Server) | ✅ | ✅ |
| Rollen & Rechte (Admin, Chef/Chefin, Büro, Werkstatt, Mitarbeiter; Bereiche sehen/ändern, Sonderrechte; serverseitig in `core/permissions.py` + `module_guard`) | ✅ | ✅ |
| Server-Betrieb Hetzner (docker-compose.prod.yml, https/Caddy, Härtung, PWA) – docs/ANLEITUNG_SERVER.md | ✅ | ✅ |
| Storno → Auftrag korrigieren → neue Rechnung (Verweis Rechnungsposition ON DELETE SET NULL) | ✅ | ✅ |
| Dokumentenmanagement | ✅ | ✅ |
| Audit-Log | ✅ | ✅ |
| Einstellungen | ✅ | ✅ |
| Angebote / Kostenvoranschläge | ✅ | ✅ |
| Inventur (Blindzählung, Differenzbuchung, Inventurliste PDF/CSV) | ✅ | ✅ |
| Bestellwesen (Bestellvorschlag, Bestellung PDF/E-Mail, Wareneingang mit Teillieferung) | ✅ | ✅ |
| E-Rechnung: ZUGFeRD-Ausgang (EN16931, PDF/A-3) | ✅ | ✅ |
| E-Rechnung: Eingang (ZUGFeRD + XRechnung UBL/CII, GoBD-Archiv) | ✅ | ✅ |
| Hilfe-Center + KI-Assistent (Claude Haiku, optional; Fallback Stichwortsuche) | ✅ | ✅ |
| Automatische Tests (pytest, vitest, E2E) – siehe docs/TESTS.md | ✅ | ✅ |

## Module (noch offen)

- XRechnung-Ausgang für Behörden (Leitweg-ID) – erst bei Bedarf
- OCR Engine
- Redis / Worker / Scheduler
- Mailversand (Mailjet)
- Monitoring (Checkly / Sentry)
- DSGVO Datenexport und -löschung

---

## Coding-Konventionen

### Python (Backend)
- snake_case für Variablen und Funktionen
- PascalCase für Klassen
- Docstrings bei allen Funktionen (deutsch)
- Type Hints überall verwenden
- Neue Endpunkte immer in `backend/app/api/v1/<modul>.py`
- Neue Modelle immer in `backend/app/models/<modul>.py`
- Neue Schemas immer in `backend/app/schemas/<modul>.py`
- Bei neuen Datenbankfeldern immer eine Alembic-Migration erstellen

### TypeScript (Frontend)
- camelCase für Variablen und Funktionen
- PascalCase für Komponenten und Interfaces
- API-Aufrufe nur über `frontend/src/api/client.ts`
- Kein direktes `fetch()` in Komponenten
- Neue Seiten in `frontend/src/pages/`
- Neue Komponenten in `frontend/src/components/`

### Allgemein
- Keine Magic Numbers – Konstanten mit Namen definieren
- Fehlermeldungen immer auf Deutsch
- Keine `console.log` im Produktionscode

---

## Datenbank-Konventionen
- UUID als Primary Key (kein Integer)
- `created_at` und `updated_at` in allen Tabellen (via BaseModel)
- Soft-Delete wo sinnvoll (status = 'cancelled' statt löschen)
- Audit-Log bei allen wichtigen Änderungen

---

## Wichtige Hinweise
- DSGVO und GoBD Konformität beachten
- Rechnungen sind unveränderlich nach Erstellung (GoBD)
- Alle Änderungen an Rechnungen, Kunden, Fahrzeugen ins Audit-Log
- Passwörter nur als bcrypt-Hash speichern
- API immer mit JWT-Auth absichern (außer /health und Webhook-Endpunkte)

---

## Externe Schnittstellen
- **Termin-Marktplatz.de** – Webhook für Terminimport (bereits implementiert)
  - Webhook-URL: `/api/v1/appointments/webhook/termin-marktplatz`
  - Auth: X-API-Key Header
- **Mailjet** – geplant für E-Mail-Versand (noch nicht implementiert)

---

## Lokale Entwicklung starten
```bash
# Backend
cd backend
pip install -r requirements.txt
alembic upgrade head
python scripts/init_db.py
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Docker (Produktion)
```bash
docker compose up -d
```
