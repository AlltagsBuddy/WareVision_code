# Genaue Anleitung: Schritt 5 – Projekt starten und testen

**Ziel:** Backend und Frontend lokal starten und prüfen, dass alles funktioniert.

---

## Übersicht

| Phase | Dauer | Was passiert |
|-------|-------|--------------|
| A | 2 Min | Voraussetzungen prüfen |
| B | 5 Min | PostgreSQL vorbereiten |
| C | 5 Min | Backend starten |
| D | 3 Min | Frontend starten |
| E | 2 Min | Login testen |

---

## Phase A: Voraussetzungen prüfen

### A.1 Python prüfen

1. **Terminal öffnen** (PowerShell oder CMD)
   - Windows: `Win + R` → `powershell` → Enter
   - Oder: Rechtsklick auf Start → „Windows PowerShell“

2. **Befehl eingeben:**
   ```
   python --version
   ```

3. **Erwartete Ausgabe:**
   ```
   Python 3.12.x
   ```
   (oder 3.11, 3.13 – mindestens 3.11)

4. **Falls Fehler** „python wird nicht erkannt“:
   - Python installieren: https://www.python.org/downloads/
   - Bei Installation: **„Add Python to PATH“** aktivieren
   - Terminal neu öffnen

---

### A.2 Node.js prüfen

1. **Im gleichen Terminal:**
   ```
   node --version
   ```

2. **Erwartete Ausgabe:**
   ```
   v18.x.x
   ```
   (oder höher)

3. **Falls Fehler** „node wird nicht erkannt“:
   - Node.js installieren: https://nodejs.org/ (LTS-Version)
   - Terminal neu öffnen

---

### A.3 npm prüfen

1. **Befehl:**
   ```
   npm --version
   ```

2. **Erwartete Ausgabe:** z.B. `10.x.x`

---

### A.4 PostgreSQL prüfen

1. **Befehl:**
   ```
   psql --version
   ```

2. **Erwartete Ausgabe:** z.B. `psql (PostgreSQL) 16.x`

3. **Falls Fehler:** PostgreSQL ist nicht im PATH oder nicht installiert.
   - Installieren: https://www.postgresql.org/download/windows/
   - Oder: pgAdmin nutzen (kommt mit PostgreSQL) – siehe Phase B

---

## Phase B: PostgreSQL vorbereiten

Die Datenbank `warevision` muss existieren, bevor das Backend startet.

### Option 1: Mit psql (wenn installiert)

1. **Terminal öffnen**

2. **Als PostgreSQL-Admin verbinden** (Passwort beim Installieren gesetzt):
   ```
   psql -U postgres
   ```

3. **In der psql-Konsole nacheinander ausführen:**
   ```sql
   CREATE USER warevision WITH PASSWORD 'warevision';
   CREATE DATABASE warevision OWNER warevision;
   \q
   ```

4. **Fertig.** Die Datenbank `warevision` existiert jetzt.

---

### Option 2: Mit pgAdmin (grafisch)

1. **pgAdmin starten** (Startmenü → pgAdmin 4)

2. **Links:** Server auswählen (z.B. „PostgreSQL 16“) → Verbindung herstellen (Master-Passwort eingeben)

3. **Rechtsklick auf „Databases“** → Create → Database

4. **Eingeben:**
   - Database: `warevision`
   - Owner: `postgres` (oder neuen User anlegen)
   - Save

5. **User anlegen** (falls noch nicht vorhanden):
   - Links: Login/Group Roles → Rechtsklick → Create → Login/Group Role
   - General: Name = `warevision`
   - Definition: Password = `warevision`
   - Privileges: Can login = Yes
   - Save

6. **Datenbank-Owner setzen** (optional):
   - Rechtsklick auf `warevision` → Properties → Security
   - Owner auf `warevision` setzen

---

### Option 3: Mit Docker (falls Docker installiert)

1. **Terminal:**
   ```
   cd d:\WareVision\WareVision_code
   docker compose up -d postgres
   ```

2. **Warten** bis Container läuft (ca. 30 Sekunden)

3. **Datenbank** `warevision` wird automatisch erstellt (User: `warevision`, Passwort: `warevision`)

---

## Phase C: Backend starten

### C.1 Zum Projektordner wechseln

1. **Terminal öffnen** (oder neu öffnen)

2. **Befehl:**
   ```
   cd d:\WareVision\WareVision_code\backend
   ```

3. **Prüfen:** Aktueller Pfad sollte mit `...\backend` enden:
   ```
   pwd
   ```
   (PowerShell) oder `cd` (CMD)

---

### C.2 Virtuelle Umgebung erstellen

1. **Befehl:**
   ```
   python -m venv .venv
   ```

2. **Erwartete Ausgabe:** Keine (oder kurze Meldung)

3. **Prüfen:** Ordner `backend\.venv` existiert jetzt

---

### C.3 Virtuelle Umgebung aktivieren

**PowerShell:**
```
.\.venv\Scripts\Activate.ps1
```

**CMD:**
```
.venv\Scripts\activate.bat
```

**Erwartete Ausgabe:** Die Zeile beginnt mit `(.venv)`:
```
(.venv) PS D:\WareVision\WareVision_code\backend>
```

**Falls Fehler** „Ausführung von Skripts ist deaktiviert“:
```
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Dann C.3 nochmal ausführen.

---

### C.4 Abhängigkeiten installieren

1. **Befehl:**
   ```
   pip install -r requirements.txt
   ```

2. **Warten** (ca. 1–2 Minuten)

3. **Erwartete Ausgabe am Ende:**
   ```
   Successfully installed ...
   ```

---

### C.5 Umgebungsvariable setzen (falls PostgreSQL anders konfiguriert)

**Standard:** Datenbank `warevision` auf `localhost:5432`, User `warevision`, Passwort `warevision`

**Falls anders:** Datei `.env` im Ordner `backend` anlegen:

1. **Datei kopieren:**
   ```
   copy .env.example .env
   ```

2. **`.env` bearbeiten** und `DATABASE_URL` anpassen, z.B.:
   ```
   DATABASE_URL=postgresql://warevision:warevision@localhost:5432/warevision
   ```

---

### C.6 Datenbank initialisieren

1. **Befehl:**
   ```
   python scripts\init_db.py
   ```

2. **Erwartete Ausgabe:**
   ```
   Creating tables...
   Roles and admin user created.
   Login: admin@warevision.local / admin123
   Done.
   ```

3. **Falls Fehler** „connection refused“ oder „could not connect“:
   - PostgreSQL läuft nicht → Starten
   - Datenbank `warevision` fehlt → Phase B wiederholen
   - User/Passwort falsch → `.env` prüfen

---

### C.7 Backend starten

1. **Befehl:**
   ```
   uvicorn app.main:app --reload
   ```

2. **Erwartete Ausgabe:**
   ```
   INFO:     Uvicorn running on http://127.0.0.1:8000
   INFO:     Application startup complete.
   ```

3. **Backend läuft.** Dieses Terminal **nicht schließen**.

---

### C.8 Backend prüfen

1. **Browser öffnen**

2. **Adresse eingeben:**
   ```
   http://localhost:8000
   ```

3. **Erwartete Anzeige:** JSON mit `{"message":"WareVision API",...}`

4. **API-Dokumentation öffnen:**
   ```
   http://localhost:8000/docs
   ```

5. **Erwartete Anzeige:** Swagger UI mit allen Endpoints

6. **Health-Check:**
   ```
   http://localhost:8000/health
   ```
   Erwartete Anzeige: `{"status":"ok","app":"WareVision"}`

---

## Phase D: Frontend starten

**Wichtig:** Backend muss weiterhin laufen (Terminal 1 offen lassen).

### D.1 Neues Terminal öffnen

1. **Zweites Terminal öffnen**
   - In VS Code/Cursor: Terminal → New Terminal
   - Oder: Neue PowerShell/CMD-Instanz

2. **Zum Frontend wechseln:**
   ```
   cd d:\WareVision\WareVision_code\frontend
   ```

---

### D.2 Abhängigkeiten installieren

1. **Befehl:**
   ```
   npm install
   ```

2. **Warten** (ca. 1–2 Minuten)

3. **Erwartete Ausgabe am Ende:**
   ```
   added XXX packages
   ```

---

### D.3 Frontend starten

1. **Befehl:**
   ```
   npm run dev
   ```

2. **Erwartete Ausgabe:**
   ```
   VITE v5.x.x  ready in 500 ms
   ➜  Local:   http://localhost:5173/
   ```

3. **Frontend läuft.** Dieses Terminal **nicht schließen**.

---

### D.4 Frontend prüfen

1. **Browser öffnen** (oder neuen Tab)

2. **Adresse eingeben:**
   ```
   http://localhost:5173
   ```

3. **Erwartete Anzeige:** Login-Seite von WareVision mit „WareVision“ und „Warenwirtschafts- und Werkstattsystem“

---

## Phase E: Login testen

### E.1 Einloggen

1. **Auf der Login-Seite** (http://localhost:5173):

2. **E-Mail eingeben:**
   ```
   admin@warevision.local
   ```

3. **Passwort eingeben:**
   ```
   admin123
   ```

4. **Button „Anmelden“ klicken**

5. **Erwartete Anzeige:** Dashboard mit „Willkommen, Admin“ und Karten (Kunden, Mindestbestand)

---

### E.2 Navigation prüfen

1. **Oben in der Navigation** klicken:
   - Dashboard
   - Kunden
   - Fahrzeuge
   - Artikel
   - Lager

2. **Erwartete Anzeige:** Jede Seite lädt ohne Fehler (Leere Tabellen sind ok)

---

### E.3 Abmelden

1. **Rechts oben:** „Abmelden“ klicken

2. **Erwartete Anzeige:** Zurück zur Login-Seite

---

## Zusammenfassung: Beide Terminals

| Terminal 1 (Backend) | Terminal 2 (Frontend) |
|---------------------|------------------------|
| `cd d:\WareVision\WareVision_code\backend` | `cd d:\WareVision\WareVision_code\frontend` |
| `.\.venv\Scripts\Activate.ps1` | – |
| `uvicorn app.main:app --reload` | `npm run dev` |
| **Läuft auf Port 8000** | **Läuft auf Port 5173** |

---

## Checkliste: Alles erledigt?

- [ ] Python, Node.js, npm installiert und im PATH
- [ ] PostgreSQL läuft, Datenbank `warevision` existiert
- [ ] `python scripts\init_db.py` erfolgreich
- [ ] Backend startet (`uvicorn app.main:app --reload`)
- [ ] http://localhost:8000/docs erreichbar
- [ ] Frontend startet (`npm run dev`)
- [ ] http://localhost:5173 zeigt Login-Seite
- [ ] Login mit admin@warevision.local / admin123 funktioniert
- [ ] Dashboard und Navigation funktionieren

---

## Fehlerbehebung

### Backend: „ModuleNotFoundError: No module named 'app'“

1. **Im Ordner `backend` sein:** `cd d:\WareVision\WareVision_code\backend`
2. **Virtuelle Umgebung aktiviert:** Zeile beginnt mit `(.venv)`

---

### Backend: „connection refused“ oder „could not connect to server“

- PostgreSQL-Dienst starten (Dienste → postgresql-x64-16)
- Oder: `docker compose up -d postgres` (falls Docker)

---

### Frontend: „npm wird nicht erkannt“

- Node.js neu installieren („Add to PATH“)
- Terminal neu öffnen

---

### Frontend: „Failed to fetch“ oder „Network Error“ beim Login

- Backend läuft auf Port 8000?
- Prüfen: http://localhost:8000/health
- Frontend-Proxy: `vite.config.ts` enthält Proxy für `/api` → `http://localhost:8000`

---

### Login: „Ungültige E-Mail oder Passwort“

- Datenbank initialisiert? `python scripts\init_db.py` erneut ausführen
- E-Mail exakt: `admin@warevision.local` (kein Leerzeichen)
- Passwort: `admin123`

---

*Erstellt am 10.03.2026 für WareVision*
