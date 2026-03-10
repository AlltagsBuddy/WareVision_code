# WareVision

**Warenwirtschafts- und Werkstattsystem** – webbasierte Software für Kunden-, Fahrzeug-, Artikel- und Lagerverwaltung, Werkstattaufträge, Termine und Rechnungen.

## Technologie-Stack

- **Frontend:** React + TypeScript (Vite)
- **Backend:** FastAPI (Python)
- **Datenbank:** PostgreSQL
- **Deployment:** Docker

## Schnellstart

### Voraussetzungen

- Python 3.12+
- PostgreSQL 16+
- Node.js 18+ (für Frontend)

### Backend starten

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

Datenbank erstellen und initialisieren:

```bash
# PostgreSQL: Datenbank "warevision" anlegen
# Dann:
python scripts/init_db.py
```

Backend starten:

```bash
uvicorn app.main:app --reload
```

**API:** http://localhost:8000  
**Docs:** http://localhost:8000/docs

### Frontend starten

```bash
cd frontend
npm install
npm run dev
```

**Frontend:** http://localhost:5173

### Standard-Login

- **E-Mail:** admin@warevision.local  
- **Passwort:** admin123

### Docker

```bash
docker compose up -d postgres
# Backend und Frontend lokal starten (siehe oben)
```

## Projektstruktur

```
WareVision_code/
├── backend/          # FastAPI
│   ├── app/
│   │   ├── api/      # REST Endpoints
│   │   ├── core/     # Config, DB, Security
│   │   ├── models/   # SQLAlchemy
│   │   └── schemas/  # Pydantic
│   ├── alembic/      # Migrationen
│   └── scripts/      # init_db etc.
├── frontend/         # React + TypeScript
├── docs/             # Dokumentation
└── docker-compose.yml
```

## Module

- **Kunden** – CRUD, Dublettenprüfung
- **Fahrzeuge** – Kunde → n Fahrzeuge
- **Artikel** – Stammdaten, Barcode
- **Lager** – Wareneingang/-ausgang, Mindestbestand
- **Werkstattaufträge** – (geplant)
- **Terminplaner** – (geplant)
- **Rechnungen** – (geplant)

## Lizenz

Proprietär – Quad Paradies Schoner
