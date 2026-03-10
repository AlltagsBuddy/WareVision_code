# Schritt 0: Projektstruktur – Kurzreferenz

**Vollständige Anleitung:** [ANLEITUNG_PROJEKTSTRUKTUR.md](./ANLEITUNG_PROJEKTSTRUKTUR.md)

---

## Was du jetzt tun musst (nur 2 Schritte)

### 1. Git initialisieren

```powershell
cd d:\WareVision\WareVision_code
git init
git add .
git commit -m "chore: initial project structure"
```

### 2. Projekt testen

**Backend:**
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\init_db.py
uvicorn app.main:app --reload
```

**Frontend (neues Terminal):**
```powershell
cd frontend
npm install
npm run dev
```

**Login:** admin@warevision.local / admin123

---

## Bereits erledigt (durch AI)

- ✅ Ordnerstruktur (frontend, backend, infra, docs)
- ✅ README.md
- ✅ Coding-Guidelines
- ✅ .gitignore
- ✅ Backend- und Frontend-Code
