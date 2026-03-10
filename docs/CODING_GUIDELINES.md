# WareVision – Coding Guidelines

**Version:** 1.0 | **Datum:** 10.03.2026

---

## 1. Allgemein

- **Sprache:** Code-Kommentare und Commit-Messages auf Deutsch oder Englisch
- **Formatierung:** Automatisch (Prettier für Frontend, Black/Ruff für Backend empfohlen)

---

## 2. Git & Commits

### Conventional Commits

Format: `typ(bereich): beschreibung`

| Typ | Bedeutung |
|-----|-----------|
| `feat` | Neues Feature |
| `fix` | Bugfix |
| `docs` | Dokumentation |
| `chore` | Wartung, Konfiguration |
| `refactor` | Refactoring ohne Funktionsänderung |
| `test` | Tests |

**Beispiele:**
```
feat(customers): Dublettenprüfung hinzugefügt
fix(articles): Barcode-Suche korrigiert
docs: README aktualisiert
chore: Projektstruktur angelegt
```

### Branching

- `main` – Produktionsstand
- `develop` – Entwicklung
- `feature/xyz` – Feature-Branches
- `fix/xyz` – Bugfix-Branches

---

## 3. Backend (Python / FastAPI)

### Struktur

```
backend/app/
├── api/         # HTTP-Layer, keine Businesslogik
├── core/        # Config, DB, Security
├── models/      # SQLAlchemy-Modelle
├── schemas/     # Pydantic (Request/Response)
├── services/    # Businesslogik (später)
└── repositories/# Datenbankzugriff (später)
```

### Namenskonventionen

- **Dateien:** `snake_case.py`
- **Klassen:** `PascalCase`
- **Funktionen/Variablen:** `snake_case`
- **Konstanten:** `UPPER_SNAKE_CASE`

### API-Endpoints

- REST, Plural: `/api/v1/customers`, `/api/v1/articles`
- HTTP-Methoden: GET (Lesen), POST (Erstellen), PATCH (Aktualisieren), DELETE (Löschen)

---

## 4. Frontend (React / TypeScript)

### Struktur

```
frontend/src/
├── api/         # API-Client
├── components/  # Wiederverwendbare Komponenten
├── hooks/       # Custom Hooks
├── pages/       # Seiten/Routen
└── main.tsx
```

### Namenskonventionen

- **Dateien:** `PascalCase.tsx` für Komponenten, `camelCase.ts` für Utils
- **Komponenten:** `PascalCase`
- **Hooks:** `useCamelCase`

---

## 5. Datenbank

- **Tabellen:** `snake_case` (z.B. `workshop_orders`)
- **Spalten:** `snake_case` (z.B. `created_at`)
- **Primärschlüssel:** `id` (UUID)
- **Migrationen:** Immer über Alembic, keine manuellen Änderungen

---

## 6. Sicherheit

- Keine Secrets im Code (`.env` nutzen)
- Passwörter nur gehasht speichern
- API-Endpoints authentifizieren (JWT)

---

*Bei Fragen: siehe Roadmap oder Lastenheft.*
