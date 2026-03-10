# WareVision – Detaillierte Sprint-Roadmap

**2-Wochen-Sprints | Priorität P0 → P1 → P2**

---

## Sprint-Übersicht

| Sprint | Phase | Epics | Fokus |
|--------|-------|-------|-------|
| 1 | Projekt-Setup | Epic 0 | Repository, Struktur, Konventionen |
| 2 | Infrastruktur | Epic 1 | Hetzner, Docker, Reverse Proxy |
| 3 | DevOps | Epic 2 | GitLab, CI/CD Pipeline |
| 4 | Backend Basis | Epic 3 | FastAPI, PostgreSQL, Redis |
| 5 | Auth | Epic 4 | User, Login, JWT, Rollen |
| 6 | Stammdaten 1 | Epic 5, 6 | Kunden, Fahrzeuge |
| 7 | Stammdaten 2 | Epic 7, 8 | Artikel, Lager |
| 8 | Werkstatt | Epic 9 | Werkstattaufträge |
| 9 | Termine | Epic 10 | Kalender, Konfliktprüfung |
| 10 | Termin-Marktplatz | Epic 11 | Import, Dublettenschutz |
| 11 | Rechnungen | Epic 12 | Rechnungsmodell, PDF |
| 12 | Dokumente | Epic 13 | Upload, OCR |
| 13 | Scan & E-Rechnung | Epic 14, 15 | QR/Barcode, ZUGFeRD |
| 14 | Wartung & Compliance | Epic 16, 17, 18, 19 | Wartungspläne, Monitoring, Audit, Backup |

---

## Epic-Story-Matrix (Tasks & DoD)

### Epic 0 – Projekt-Setup (P0)

| Story | Tasks | DoD |
|-------|-------|-----|
| **0.1** | Git-Repo erstellen, Branching (main/develop/feature), .gitignore, Conventional Commits | Repo initialisiert, Strategie dokumentiert |
| **0.2** | Ordnerstruktur (frontend/backend/infra/docs), README, Coding-Guidelines | Struktur vorhanden, Entwickler können klonen & starten |

---

### Epic 1 – Infrastruktur (P0)

| Story | Tasks | DoD |
|-------|-------|-----|
| **1.1** | Hetzner Cloud-Projekt, Server Nürnberg, Firewall, SSH-Keys, Backups | Server erreichbar, Root-Login deaktiviert |
| **1.2** | Docker, Docker Compose, Compose-Projektstruktur | `docker compose up` startet |
| **1.3** | Reverse Proxy, HTTPS, Let's Encrypt | Webserver unter HTTPS erreichbar |

---

### Epic 2 – DevOps (P0)

| Story | Tasks | DoD |
|-------|-------|-----|
| **2.1** | GitLab self-hosted, Runner, Container Registry | GitLab erreichbar, Runner läuft |
| **2.2** | Build Pipeline, Tests, Docker Image, Deployment Script | Push → Build → Deploy automatisch |

---

### Epic 3 – Backend Grundsystem (P0)

| Story | Tasks | DoD |
|-------|-------|-----|
| **3.1** | FastAPI Projekt, Modulstruktur, Healthcheck | `/health` liefert Status |
| **3.2** | PostgreSQL Container, ORM, Alembic | Migrationen laufen automatisch |
| **3.3** | Redis Container, Background Worker | Hintergrundjobs ausführbar |

---

### Epic 4 – Authentifizierung (P0)

| Story | Tasks | DoD |
|-------|-------|-----|
| **4.1** | User-Tabelle, Passwort-Hashing, Benutzer-API | Benutzer anlegen/ändern möglich |
| **4.2** | Login Endpoint, JWT, Token-Validierung | Authentifizierte Requests möglich |
| **4.3** | Role-Tabelle, Berechtigungsprüfung | Endpoints rollenabhängig geschützt |

---

### Epic 5 – Kundenverwaltung (P0)

| Story | Tasks | DoD |
|-------|-------|-----|
| **5.1** | Tabelle `customers`, CRUD API | Kunde erstellen/bearbeiten/löschen |
| **5.2** | Dublettensuche, Warnhinweis | Dubletten werden erkannt |

---

### Epic 6 – Fahrzeugverwaltung (P0)

| Story | Tasks | DoD |
|-------|-------|-----|
| **6.1** | Tabelle `vehicles`, Kunde → Fahrzeuge | Kunde kann mehrere Fahrzeuge besitzen |
| **6.2** | Historientabelle, Anzeige vergangener Aufträge | Historie sichtbar |

---

### Epic 7 – Artikelverwaltung (P0)

| Story | Tasks | DoD |
|-------|-------|-----|
| **7.1** | Tabelle `articles`, CRUD API | Artikel verwaltbar |
| **7.2** | Barcode-Feld, Scan-Endpoint | Artikel über Barcode identifizierbar |

---

### Epic 8 – Lagerverwaltung (P0)

| Story | Tasks | DoD |
|-------|-------|-----|
| **8.1** | Tabelle `stock_movements`, Buchungslogik | Wareneingang/-ausgang funktioniert |
| **8.2** | Mindestbestand-Feld, Warnlogik | Warnung bei kritischem Bestand |

---

### Epic 9 – Werkstattaufträge (P0)

| Story | Tasks | DoD |
|-------|-------|-----|
| **9.1** | Tabelle `workshop_orders`, Positionen | Werkstattauftrag erstellbar |
| **9.2** | Arbeitszeitfeld, Summenberechnung | Arbeitszeit korrekt berechnet |

---

### Epic 10 – Terminplaner (P0)

| Story | Tasks | DoD |
|-------|-------|-----|
| **10.1** | Terminmodell, Kalenderansicht | Termine sichtbar |
| **10.2** | Terminüberschneidung prüfen | Doppelbuchungen verhindert |

---

### Epic 11 – Termin-Marktplatz (P0)

| Story | Tasks | DoD |
|-------|-------|-----|
| **11.1** | Endpoint für Terminimport, Authentifizierung | Externe Termine importiert |
| **11.2** | Externe ID speichern | Termin nicht doppelt importiert |

---

### Epic 12 – Rechnungen (P0)

| Story | Tasks | DoD |
|-------|-------|-----|
| **12.1** | Tabelle `invoices`, Positionen | Rechnung erstellbar |
| **12.2** | PDF Template, PDF speichern | Rechnung als PDF exportierbar |

---

### Epic 13 – Dokumentenmanagement (P1)

| Story | Tasks | DoD |
|-------|-------|-----|
| **13.1** | Upload Endpoint, Speicherung | Dokumente abrufbar |
| **13.2** | OCR Worker, Textextraktion | Dokumenttext extrahiert |

---

### Epic 14 – QR/Barcode Scan (P1)

| Story | Tasks | DoD |
|-------|-------|-----|
| **14.1** | Kamera API, Scan UI | Artikel per Kamera scanbar |

---

### Epic 15 – E-Rechnung (P1)

| Story | Tasks | DoD |
|-------|-------|-----|
| **15.1** | XML-Struktur, PDF+XML kombinieren | ZUGFeRD Rechnung erzeugt |

---

### Epic 16 – Wartungspläne (P2)

| Story | Tasks | DoD |
|-------|-------|-----|
| **16.1** | Tabelle `maintenance_plans`, Aufgabenliste | Wartungsplan speicherbar |
| **16.2** | Webabruf, Parser | Wartungsplan automatisch generiert |

---

### Epic 17 – Monitoring (P1)

| Story | Tasks | DoD |
|-------|-------|-----|
| – | Uptime Checks, API Monitoring, Error Tracking (Checkly, Sentry) | Fehler werden automatisch gemeldet |

---

### Epic 18 – Sicherheit / Compliance (P1)

| Story | Tasks | DoD |
|-------|-------|-----|
| **18.1** | Tabelle `audit_logs`, Änderungen speichern | Änderungen nachvollziehbar |
| **18.2** | Datenexport, Löschfunktion | DSGVO Anforderungen erfüllt |

---

### Epic 19 – Backups (P0)

| Story | Tasks | DoD |
|-------|-------|-----|
| **19.1** | Tägliche Dumps, automatischer Upload | DB Backups vorhanden |
| **19.2** | Backup wiederherstellen | Restore funktioniert |

---

## Empfohlene Reihenfolge der Epics

1. Epic 0 → 2. Epic 1 → 3. Epic 2 → 4. Epic 3 → 5. Epic 4 → 6. Epic 5 → 7. Epic 6 → 8. Epic 7 → 9. Epic 8 → 10. Epic 9 → 11. Epic 12 → 12. Epic 10 → 13. Epic 11 → 14. Epic 13 → 15. Epic 15 → 16. Epic 14 → 17. Epic 16 → 18. Epic 17–19

---

*Erstellt am 10.03.2026 für WareVision*
