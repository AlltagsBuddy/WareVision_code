# WareVision

**Warenwirtschafts- und Werkstattsystem** – webbasierte Software für Kunden-, Fahrzeug-, Artikel- und Lagerverwaltung, Werkstattaufträge, Termine und Rechnungen.

## Technologie-Stack

- **Frontend:** React + TypeScript (Vite)
- **Backend:** FastAPI (Python)
- **Datenbank:** PostgreSQL
- **Deployment:** Docker

## Schnellstart mit Docker

```bash
docker compose up -d --build
```

Falls der Build mit `failed to fetch oauth token` / `auth.docker.io` fehlschlägt: Die Dockerfiles nutzen `mirror.gcr.io` (Google-Spiegel der offiziellen Images). Erneut bauen; bei anhaltenden Netzproblemen VPN aus/an oder [lokale Entwicklung](#lokale-entwicklung) ohne vollständigen Image-Build nutzen.

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API-Dokumentation:** http://localhost:8000/docs

**Login:** admin@warevision.local / admin123

## Testen von verschiedenen Systemen

WareVision kann einfach von verschiedenen Geräten (PC, Tablet, Smartphone) oder aus anderen Netzwerken getestet werden:

- **Link:** `http://<SERVER-IP>:5173` (z.B. `http://192.168.1.100:5173`)
- **Zugangsdaten:** admin@warevision.local / admin123
- **Login mit vorausgefüllter E-Mail:** `http://<SERVER-IP>:5173/login?email=admin@warevision.local`

Details siehe [docs/TEST_ZUGANG.md](docs/TEST_ZUGANG.md).

## Lokale Entwicklung

### Voraussetzungen

- Python 3.12+
- PostgreSQL 16+
- Node.js 18+

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
python scripts/init_db.py
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Datenbank

PostgreSQL-Datenbank `warevision` mit User `warevision` / Passwort `warevision` anlegen. Details siehe `docs/ANLEITUNG_SCHRITT5_PROJEKT_TESTEN.md`.

## Projektstruktur

```
WareVision_code/
├── backend/          # FastAPI
│   ├── app/
│   │   ├── api/      # REST Endpoints
│   │   ├── core/     # Config, DB, Security
│   │   ├── models/   # SQLAlchemy
│   │   ├── schemas/  # Pydantic
│   │   └── services/ # PDF etc.
│   ├── alembic/      # Migrationen
│   └── scripts/      # init_db
├── frontend/         # React + TypeScript
├── docs/             # Dokumentation
└── docker-compose.yml
```

## Module

| Modul | Funktionen |
|-------|------------|
| **Kunden** | CRUD, Dublettenprüfung, Adressen |
| **Fahrzeuge** | Kunde → n Fahrzeuge, Historie |
| **Artikel** | Stammdaten, Barcode-Suche |
| **Lager** | Wareneingang/-ausgang, Mindestbestand, Barcode-Scan |
| **Werkstattaufträge** | CRUD, Positionen (Arbeit/Teile), Termin-Verknüpfung, Rechnung erstellen |
| **Wartungspläne** | Pläne nach Hersteller/Modell, Aufgaben |
| **Terminplaner** | Kalender, Anlegen, Stornieren |
| **Rechnungen** | Erstellen aus Auftrag/manuell, PDF, Ausstellen, Mahnwesen |
| **Dokumente** | Upload, Zuordnung Kunde/Fahrzeug |
| **Benutzer** | Verwaltung (Admin) |

## Lizenz

Proprietär – Quad Paradies Schoner
