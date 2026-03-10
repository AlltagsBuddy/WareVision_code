# WareVision – Lastenheft (Referenz)

**Warenwirtschafts- und Werkstattsystem**  
Version: 1.0 | Datum: 09.03.2026

---

## 1. Ziel des Systems

Webbasierte Software zur Verwaltung von:

- Kunden
- Fahrzeugen (Quads / Motorräder)
- Artikeln und Lagerbestand
- Werkstattaufträgen
- Wartungsplänen
- Rechnungen (inkl. ZUGFeRD)
- Terminen

**Anforderungen:** mobil nutzbar, automatisierte Abläufe, DSGVO- und GoBD-konform, eigene Infrastruktur.

---

## 2. Architektur

- **Modell:** Modularer Monolith
- **Hosting:** Hetzner (Nürnberg), Cloud Server CPX31
- **Stack:** React + TypeScript, FastAPI, PostgreSQL, Redis, Docker

---

## 3. Benutzerrollen

| Rolle | Berechtigungen |
|-------|----------------|
| **Administrator** | System, Benutzer, Artikel, Rechnungen, Einstellungen |
| **Werkstatt** | Werkstattaufträge, Wartungsplan, Fahrzeughistorie, Teileverbrauch |

---

## 4. Kernmodule

| Modul | Funktionen |
|-------|------------|
| Kundenverwaltung | Anlegen, Bearbeiten, Dublettenprüfung, Historie |
| Fahrzeugverwaltung | Kunde → n Fahrzeuge, VIN, Kennzeichen, Kilometerstand |
| Artikelverwaltung | Artikelstamm, EK/VK, MwSt, Lagerbestand, Barcode |
| Lagerverwaltung | Wareneingang, -ausgang, Korrektur, Mindestbestand |
| Werkstattauftrag | Auftrag, Fahrzeug, Wartungsplan, Teile, Arbeitszeit |
| Wartungsplan | Generierung nach Marke/Modell/Baujahr/Kilometer |
| Terminplaner | Kalender, Anlegen, Verschieben, Löschen |
| Termin-Marktplatz | Integration Terminmarktplatz.de (Import, Update, Storno) |
| Rechnungsmodul | Rechnung, Positionen, Werkstattübernahme, PDF |
| E-Rechnung | ZUGFeRD Export/Import, Archivierung |
| Dokumentenmanagement | Upload, OCR, Zuordnung Kunde/Fahrzeug |

---

## 5. Wichtige Tabellen

`users`, `roles`, `customers`, `customer_addresses`, `vehicles`, `manufacturers`, `vehicle_models`, `articles`, `stock_movements`, `workshop_orders`, `workshop_order_items`, `appointments`, `invoices`, `invoice_items`, `documents`, `document_ocr_results`, `maintenance_plans`, `maintenance_tasks`, `audit_logs`

---

## 6. Sicherheit & Compliance

- HTTPS, sichere Passworthashes, rollenbasierte Zugriffe
- Audit Logs, Zugriffshistorie
- DSGVO: Datenexport, Löschung, Protokolle, Verschlüsselung
- GoBD: Unveränderbarkeit Rechnungen, Protokollierung, Archivierung

---

## 7. Externe Dienste

- **Mail:** Mailjet (Passwort Reset, Termine, Rechnungen)
- **Monitoring:** Checkly (Server, API, Webfrontend, Cronjobs)
- **Fehlertracking:** Self-hosted Sentry
- **CI/CD:** Self-hosted GitLab

---

## 8. Container

`reverse-proxy`, `frontend`, `backend`, `postgres`, `redis`, `worker`, `scheduler`, `ocr`, `sentry`, `gitlab`

---

*Vollständiges Lastenheft siehe Projektunterlagen. Änderungen als Change Request.*
