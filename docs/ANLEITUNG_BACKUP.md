# WareVision – Datenbank-Backup (Epic 19)

**Ziel:** Tägliche Backups der PostgreSQL-Datenbank **und der Dateien** (Belegarchiv, E-Rechnungs-Originale, Dokumente) für GoBD-Konformität und Disaster Recovery.

> **Wichtig:** Seit dem Belegarchiv liegen die Originale aller ausgegebenen Rechnungen, Mahnungen, Angebote und Bestellungen als Dateien im Volume `uploads_data`. Das Backup erzeugt deshalb zwei Dateien: `warevision_*.dump` (Datenbank) und `warevision_dateien_*.tar.gz` (Dateien). **Beide** gehören zusammen und müssen aufbewahrt werden (Rechnungen 8 Jahre). Bitte zusätzlich regelmäßig eine Kopie außerhalb des Rechners ablegen (z. B. externe Festplatte oder verschlüsselter Cloud-Speicher).

---

## Manuelles Backup

```bash
docker compose --profile backup run --rm backup
```

*(Starten Sie zuerst die Anwendung mit `docker compose up -d`, damit die Datenbank läuft.)*

Das Backup wird in `backup_data` Volume gespeichert. Dateiname: `warevision_YYYYMMDD_HHMMSS.dump`

### Backup-Dateien anzeigen

```bash
docker compose run --rm -v backup_data:/backups alpine ls -la /backups
```

### Backup auf Host kopieren

```bash
# Linux/macOS
docker compose run --rm -v backup_data:/backups -v $(pwd):/out alpine cp /backups/warevision_20260310_120000.dump /out/

# Windows PowerShell
docker compose run --rm -v backup_data:/backups -v ${PWD}:/out alpine cp /backups/warevision_20260310_120000.dump /out/
```

---

## Tägliches Backup (Cron)

### Option 1: Host-Cron (Linux/macOS)

Crontab bearbeiten: `crontab -e`

```
0 2 * * * cd /pfad/zu/WareVision_code && docker compose --profile backup run --rm backup
```

### Option 2: Windows Task Scheduler

1. Task Scheduler öffnen
2. Neue Aufgabe: täglich um 2:00 Uhr
3. Aktion: `docker compose --profile backup run --rm backup` im Projektverzeichnis

---

## Restore (Epic 19.2)

### Voraussetzung

Backup-Datei muss im Container erreichbar sein (z.B. via Volume-Mount).

### Restore ausführen

```bash
# Backup-Datei in Volume kopieren (falls nötig)
docker compose run --rm -v backup_data:/backups -v $(pwd):/in alpine cp /in/warevision_20260310_120000.dump /backups/

# Restore (interaktiv – Bestätigung erforderlich)
docker compose run --rm -v backup_data:/backups \
  -e PGHOST=postgres -e PGUSER=warevision -e PGPASSWORD=warevision -e PGDATABASE=warevision \
  postgres:16-alpine sh -c "pg_restore -d warevision --clean --if-exists /backups/warevision_20260310_120000.dump" || true
```

**Hinweis:** `--clean` löscht bestehende Objekte. Bei Produktion vorher testen!

### Dateien wiederherstellen (Belegarchiv, Dokumente)

```bash
# Sicherung in das Backup-Volume legen (falls nötig) und in das Upload-Volume entpacken
docker compose run --rm -v backup_data:/backups -v warevision_code_uploads_data:/uploads alpine \
  sh -c "tar -xzf /backups/warevision_dateien_20260310_120000.tar.gz -C /uploads"
```

Den Volume-Namen zeigt `docker volume ls` (meist `<ordnername>_uploads_data`). Danach unter Buchhaltung → Belegarchiv auf „Archiv prüfen“ klicken.

### Restore testen

1. Backup erstellen
2. Testdaten ändern
3. Restore ausführen
4. Prüfen, ob Daten wiederhergestellt

---

## Automatischer Upload (optional)

Für Epic 19.1 "automatischer Upload" z.B. zu S3/Backblaze B2:

- Nach Backup: `rclone copy` oder `aws s3 cp` zur Cloud
- Beispiel mit rclone: Backup-Script erweitern um Upload-Schritt

---

*Erstellt am 10.03.2026 für WareVision*
