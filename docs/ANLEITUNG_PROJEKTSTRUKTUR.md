# Anleitung: Projektstruktur erstellen (Epic 0, Story 0.2)

**Ziel:** Ordnerstruktur anlegen, README erstellen, Coding-Guidelines dokumentieren.  
**Definition of Done:** Struktur vorhanden, Entwickler können Projekt klonen und starten.

---

## Übersicht: Wer macht was?

| Schritt | Aufgabe | Wer erledigt | Status |
|---------|---------|--------------|--------|
| 1 | Ordnerstruktur anlegen | **AI** (bereits erledigt) | ✅ |
| 2 | README erstellen | **AI** (bereits erledigt) | ✅ |
| 3 | Coding-Guidelines erstellen | **AI** (bereits erledigt) | ✅ |
| 4 | Git-Repository initialisieren | **Du** | ⬜ |
| 5 | Projekt klonen und testen | **Du** | ⬜ |

---

## Schritt 1: Ordnerstruktur anlegen

### Soll-Struktur (laut Roadmap)

```
WareVision_code/
├── frontend/          # React + TypeScript
├── backend/           # FastAPI (Python)
├── infra/             # Docker, CI/CD, Infrastruktur
└── docs/              # Dokumentation
```

### Was du tun musst

**Nichts.** Die Ordner und Dateien sind bereits angelegt.

### Verifizieren (optional)

Öffne den Explorer und prüfe, ob folgende Ordner existieren:

- `d:\WareVision\WareVision_code\frontend`
- `d:\WareVision\WareVision_code\backend`
- `d:\WareVision\WareVision_code\infra`
- `d:\WareVision\WareVision_code\docs`

---

## Schritt 2: README erstellen

### Was du tun musst

**Nichts.** Die Datei `README.md` im Projektroot existiert bereits.

### Verifizieren

Öffne `d:\WareVision\WareVision_code\README.md` – sie enthält Schnellstart und Projektübersicht.

---

## Schritt 3: Coding-Guidelines dokumentieren

### Was du tun musst

**Nichts.** Die Datei `docs/CODING_GUIDELINES.md` wurde erstellt.

### Verifizieren

Öffne `d:\WareVision\WareVision_code\docs\CODING_GUIDELINES.md`.

---

## Schritt 4: Git-Repository initialisieren (nur du)

### 4.1 Git installieren (falls noch nicht)

1. Öffne https://git-scm.com/download/win
2. Installiere Git für Windows
3. Nach der Installation: neues Terminal öffnen

### 4.2 Repository initialisieren

1. **Terminal öffnen** (PowerShell oder CMD)
2. **Zum Projektordner wechseln:**
   ```
   cd d:\WareVision\WareVision_code
   ```
3. **Git initialisieren:**
   ```
   git init
   ```
4. **Ersten Commit:**
   ```
   git add .
   git commit -m "chore: initial project structure"
   ```

### 4.3 Branching-Strategie (optional, für später)

- `main` = Produktion
- `develop` = Entwicklung
- `feature/*` = Feature-Branches

Branch erstellen:
```
git checkout -b develop
```

---

## Schritt 5: Projekt klonen und testen (nur du)

### 5.1 Backend testen

1. **Terminal öffnen**
2. **Zum Backend wechseln:**
   ```
   cd d:\WareVision\WareVision_code\backend
   ```
3. **Virtuelle Umgebung erstellen:**
   ```
   python -m venv .venv
   ```
4. **Virtuelle Umgebung aktivieren (PowerShell):**
   ```
   .\.venv\Scripts\Activate.ps1
   ```
   Falls Fehler: ggf. Ausführungsrichtlinie anpassen:
   ```
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```
5. **Abhängigkeiten installieren:**
   ```
   pip install -r requirements.txt
   ```
6. **PostgreSQL:** Datenbank `warevision` anlegen (z.B. pgAdmin oder `psql`)
7. **Datenbank initialisieren:**
   ```
   python scripts\init_db.py
   ```
8. **Backend starten:**
   ```
   uvicorn app.main:app --reload
   ```
9. **Prüfen:** Browser öffnen → http://localhost:8000/docs

### 5.2 Frontend testen (zweites Terminal)

1. **Neues Terminal öffnen**
2. **Zum Frontend wechseln:**
   ```
   cd d:\WareVision\WareVision_code\frontend
   ```
3. **Abhängigkeiten installieren:**
   ```
   npm install
   ```
4. **Frontend starten:**
   ```
   npm run dev
   ```
5. **Prüfen:** Browser öffnen → http://localhost:5173  
   Login: `admin@warevision.local` / `admin123`

---

## Checkliste: Definition of Done

- [ ] Ordner `frontend`, `backend`, `infra`, `docs` vorhanden
- [ ] `README.md` im Projektroot vorhanden
- [ ] `docs/CODING_GUIDELINES.md` vorhanden
- [ ] Git-Repository initialisiert (`git init`)
- [ ] Erster Commit erstellt
- [ ] Backend startet (`uvicorn app.main:app --reload`)
- [ ] Frontend startet (`npm run dev`)
- [ ] Login funktioniert

---

## Fehlerbehebung

### "python" wird nicht erkannt

- Python 3.12+ installieren: https://www.python.org/downloads/
- Bei Installation "Add Python to PATH" aktivieren

### "npm" wird nicht erkannt

- Node.js 18+ installieren: https://nodejs.org/

### PostgreSQL nicht installiert

- PostgreSQL 16 installieren: https://www.postgresql.org/download/windows/
- Datenbank `warevision` mit User `warevision` / Passwort `warevision` anlegen

### PowerShell: Ausführungsrichtlinie

```
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

*Erstellt am 10.03.2026 für WareVision*
