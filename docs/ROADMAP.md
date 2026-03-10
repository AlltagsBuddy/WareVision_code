# WareVision – Roadmap

**Warenwirtschafts- und Werkstattsystem**  
Version: 1.0 | Datum: 10.03.2026

---

## 1. Projektübersicht

### 1.1 Projektziel

Entwicklung einer webbasierten, mobil nutzbaren Werkstatt- und Warenwirtschaftssoftware **WareVision** mit:

| Bereich | Funktionen |
|---------|------------|
| **Stammdaten** | Kunden, Fahrzeuge (Quads/Motorräder), Artikel |
| **Lager** | Bestandsverwaltung, Wareneingang/-ausgang, Mindestbestand |
| **Werkstatt** | Aufträge, Arbeitszeit, Teileverbrauch |
| **Termine** | Kalender, Terminplaner, Schnittstelle Termin-Marktplatz.de |
| **Rechnung** | PDF, ZUGFeRD, GoBD-konform |
| **Dokumente** | Upload, OCR, Zuordnung |
| **Compliance** | DSGVO, GoBD, Audit Logs |

### 1.2 Unternehmensrahmen

- **Mitarbeiter:** 1 Geschäftsführer, 1 Geschäftsführerin, 1 Mechaniker
- **Standort:** Deutschland
- **Infrastruktur:** 1 Lager, 1 Werkstattbereich
- **Hosting:** Hetzner (Nürnberg), Cloud Server CPX31

### 1.3 Technologie-Stack

| Schicht | Technologie |
|---------|-------------|
| Frontend | React + TypeScript, QR/Barcode-Scanner |
| Backend | FastAPI (Python) |
| Datenbank | PostgreSQL |
| Cache/Queue | Redis |
| OCR | Self-hosted OCR Engine |
| Deployment | Docker, Caddy/Nginx |

---

## 2. Priorisierung (MUSS / SOLL / KANN)

### MUSS (MVP)

- Login, Rollen
- Kunden, Fahrzeuge, Artikel, Lager
- Werkstattauftrag
- Terminplaner
- Termin-Marktplatz-Import
- Rechnung, PDF
- ZUGFeRD Export
- OCR
- QR-/Barcode-Scan

### SOLL

- Bestandsreservierung
- Dashboard
- Mahnwesen
- Foto-Dokumentation

### KANN

- KI-Zeitvorschläge
- Automatische Nachbestellung
- Erweiterte Statistiken

---

## 3. Entwicklungsphasen & Epics

### Phase 0 – Projekt-Setup (P0)

| Epic | Story | Beschreibung | DoD |
|------|------|--------------|-----|
| **Epic 0** | 0.1 | Repository & Branching | Git-Repo, Branching-Strategie, .gitignore, Conventional Commits |
| | 0.2 | Projektstruktur | `/frontend`, `/backend`, `/infra`, `/docs`, README, Coding-Guidelines |

**Dauer:** 1 Woche

---

### Phase 1 – Infrastruktur (P0)

| Epic | Story | Beschreibung | DoD |
|------|------|--------------|-----|
| **Epic 1** | 1.1 | Hetzner Server | Cloud-Projekt, Server Nürnberg, Firewall, SSH-Keys, Backups |
| | 1.2 | Docker Umgebung | Docker, Docker Compose, `docker compose up` funktioniert |
| | 1.3 | Reverse Proxy | HTTPS, Let's Encrypt |

**Dauer:** 2 Wochen

---

### Phase 2 – DevOps / CI-CD (P0)

| Epic | Story | Beschreibung | DoD |
|------|------|--------------|-----|
| **Epic 2** | 2.1 | GitLab Installation | Self-hosted GitLab, Runner, Container Registry |
| | 2.2 | CI/CD Pipeline | Build → Test → Docker Image → Deployment |

**Dauer:** 1–2 Wochen

---

### Phase 3 – Backend Grundsystem (P0)

| Epic | Story | Beschreibung | DoD |
|------|------|--------------|-----|
| **Epic 3** | 3.1 | Backend Skeleton | FastAPI, Modulstruktur, `/health` Endpoint |
| | 3.2 | PostgreSQL Integration | Container, ORM, Alembic Migrationen |
| | 3.3 | Redis / Worker | Background Jobs (OCR, PDF, Sync) |

**Dauer:** 2 Wochen

---

### Phase 4 – Authentifizierung (P0)

| Epic | Story | Beschreibung | DoD |
|------|------|--------------|-----|
| **Epic 4** | 4.1 | Benutzerverwaltung | User-Tabelle, Passwort-Hashing, CRUD API |
| | 4.2 | Login / JWT | Login Endpoint, JWT, Token-Validierung |
| | 4.3 | Rollenmodell | Admin, Werkstatt; berechtigungsbasierter Zugriff |

**Dauer:** 1–2 Wochen

---

### Phase 5 – Stammdaten (P0)

| Epic | Story | Beschreibung | DoD |
|------|------|--------------|-----|
| **Epic 5** | 5.1 | Kundenmodell | Tabelle `customers`, CRUD API |
| | 5.2 | Dublettenprüfung | Suche, Warnhinweis bei Doppelanlage |
| **Epic 6** | 6.1 | Fahrzeugmodell | Tabelle `vehicles`, Kunde → n Fahrzeuge |
| | 6.2 | Fahrzeughistorie | Vergangene Aufträge, Teile, Kilometerstände |
| **Epic 7** | 7.1 | Artikelmodell | Tabelle `articles`, CRUD API |
| | 7.2 | Barcode / QR Code | Barcode-Feld, Scan-Endpoint |
| **Epic 8** | 8.1 | Lagerbewegungen | Wareneingang, -ausgang, Korrektur, Werkstattverbrauch |
| | 8.2 | Mindestbestand | Warnlogik bei kritischem Bestand |

**Dauer:** 3 Wochen

---

### Phase 6 – Werkstatt (P0)

| Epic | Story | Beschreibung | DoD |
|------|------|--------------|-----|
| **Epic 9** | 9.1 | Werkstattauftrag Modell | `workshop_orders`, Positionen |
| | 9.2 | Arbeitszeit erfassen | Arbeitszeitfeld, Summenberechnung |

**Dauer:** 2 Wochen

---

### Phase 7 – Terminverwaltung (P0)

| Epic | Story | Beschreibung | DoD |
|------|------|--------------|-----|
| **Epic 10** | 10.1 | Kalender | Terminmodell, Kalenderansicht |
| | 10.2 | Konfliktprüfung | Doppelbuchungen verhindern |

**Dauer:** 2 Wochen

---

### Phase 8 – Termin-Marktplatz Schnittstelle (P0)

| Epic | Story | Beschreibung | DoD |
|------|------|--------------|-----|
| **Epic 11** | 11.1 | Import API | Endpoint, Authentifizierung, Terminimport |
| | 11.2 | Dublettenschutz | Externe ID speichern, keine Doppelimporte |

**Dauer:** 1–2 Wochen

---

### Phase 9 – Rechnungen (P0)

| Epic | Story | Beschreibung | DoD |
|------|------|--------------|-----|
| **Epic 12** | 12.1 | Rechnungsmodell | `invoices`, Positionen, Rechnungsnummernlogik |
| | 12.2 | PDF Generierung | Template, PDF speichern, Export |

**Dauer:** 2 Wochen

---

### Phase 10 – Dokumente & OCR (P1)

| Epic | Story | Beschreibung | DoD |
|------|------|--------------|-----|
| **Epic 13** | 13.1 | Dokumentupload | Upload Endpoint, Speicherung, Zuordnung |
| | 13.2 | OCR Integration | OCR Worker, Textextraktion, Kundenerkennung |

**Dauer:** 2 Wochen

---

### Phase 11 – QR / Barcode Scan (P1)

| Epic | Story | Beschreibung | DoD |
|------|------|--------------|-----|
| **Epic 14** | 14.1 | Frontend Kamera | Kamera API, Scan UI, Artikel per Scan identifizieren |

**Dauer:** 1 Woche

---

### Phase 12 – E-Rechnung (P1)

| Epic | Story | Beschreibung | DoD |
|------|------|--------------|-----|
| **Epic 15** | 15.1 | ZUGFeRD Export | XML-Struktur, PDF+XML kombinieren |

**Dauer:** 1–2 Wochen

---

### Phase 13 – Wartungspläne (P2)

| Epic | Story | Beschreibung | DoD |
|------|------|--------------|-----|
| **Epic 16** | 16.1 | Wartungsmodell | `maintenance_plans`, Aufgabenliste |
| | 16.2 | Herstellerdaten Abruf | Webabruf, Parser, automatische Generierung |

**Dauer:** 2–3 Wochen

---

### Phase 14 – Monitoring & Sicherheit (P1)

| Epic | Story | Beschreibung | DoD |
|------|------|--------------|-----|
| **Epic 17** | – | Monitoring & Fehlertracking | Checkly, Sentry, Uptime, API-Monitoring |
| **Epic 18** | 18.1 | Audit Logs | Änderungen protokollieren |
| | 18.2 | DSGVO Funktionen | Datenexport, Löschfunktion |
| **Epic 19** | 19.1 | Datenbank Backup | Tägliche Dumps, automatischer Upload |
| | 19.2 | Restore Test | Backup wiederherstellen |

**Dauer:** 2 Wochen

---

## 4. Zeitplan (Übersicht)

| Phase | Inhalt | Dauer |
|-------|--------|-------|
| 0 | Projekt-Setup | 1 Woche |
| 1 | Infrastruktur | 2 Wochen |
| 2 | DevOps / CI-CD | 1–2 Wochen |
| 3 | Backend Grundsystem | 2 Wochen |
| 4 | Authentifizierung | 1–2 Wochen |
| 5 | Stammdaten (Kunden, Fahrzeuge, Artikel, Lager) | 3 Wochen |
| 6 | Werkstattaufträge | 2 Wochen |
| 7 | Terminplaner | 2 Wochen |
| 8 | Termin-Marktplatz | 1–2 Wochen |
| 9 | Rechnungen | 2 Wochen |
| 10 | Dokumente & OCR | 2 Wochen |
| 11 | QR/Barcode Scan | 1 Woche |
| 12 | ZUGFeRD | 1–2 Wochen |
| 13 | Wartungspläne | 2–3 Wochen |
| 14 | Monitoring & Sicherheit | 2 Wochen |

**Gesamtdauer MVP (P0):** ca. 16–18 Wochen (4–4,5 Monate)  
**Gesamtdauer inkl. P1/P2:** ca. 22–26 Wochen (5,5–6,5 Monate)

---

## 5. Empfohlene Sprint-Reihenfolge

### Block 1 (Sprint 1–4)
- Projekt-Setup
- Infrastruktur
- CI/CD
- Backend/Frontend Grundgerüst
- Datenbank
- Login / Rollen

### Block 2 (Sprint 5–7)
- Kunden
- Fahrzeuge
- Artikel
- Lager

### Block 3 (Sprint 8–10)
- Werkstattauftrag
- Terminplaner
- Rechnung PDF

### Block 4 (Sprint 11–12)
- Termin-Marktplatz Schnittstelle
- QR-/Barcode-Scan
- OCR Kundenerfassung

### Block 5 (Sprint 13–14)
- ZUGFeRD
- Audit
- DSGVO / GoBD

### Block 6 (Sprint 15+)
- Wartungsplanlogik
- Herstellerseiten-Abruf
- Automatisierungen

---

## 6. Sprint-Modell

- **Sprint-Länge:** 2 Wochen
- **Arbeitsweise:** Scrum-ähnlich
- **Branching:** Feature Branches, `main` / `develop`
- **Commits:** Conventional Commits

---

## 7. Abhängigkeiten

```
Projekt-Setup
    ↓
Infrastruktur → DevOps
    ↓
Backend Grundsystem (DB, Redis, Worker)
    ↓
Authentifizierung
    ↓
Stammdaten (Kunden → Fahrzeuge → Artikel → Lager)
    ↓
Werkstattaufträge ←→ Lager
    ↓
Terminplaner
    ↓
Termin-Marktplatz
    ↓
Rechnungen (aus Werkstattauftrag)
    ↓
Dokumente / OCR / QR / ZUGFeRD / Wartungspläne
```

---

## 8. Referenzen

- **Lastenheft:** `docs/LASTENHEFT.md` (Version 1.0)
- **Datenbankschema:** siehe Lastenheft / Backend-Dokumentation
- **Backend-Struktur:** `backend/app/` (FastAPI)
- **Frontend:** `frontend/` (React + TypeScript)

---

*Erstellt am 10.03.2026 für WareVision – Warenwirtschafts- und Werkstattsystem*
