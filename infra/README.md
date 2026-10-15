# Infrastruktur (infra)

Dieser Ordner enthält Infrastruktur-Konfigurationen für WareVision.

## Backup (Epic 19)

- `backup/backup.sh` – PostgreSQL-Dump-Script
- `backup/restore.sh` – Restore-Script
- Siehe `docs/ANLEITUNG_BACKUP.md` für Verwendung

## Server (Hetzner)

- `../docker-compose.prod.yml` – Betrieb auf dem Server (https, Zwei-Faktor-Pflicht)
- `server/env.example` – Vorlage für die `.env` auf dem Server
- `server/Caddyfile` – eingebauter Webserver mit automatischem https-Zertifikat
- `server/nginx-beispiel.conf`, `server/caddy-beispiel.txt` – Vorlagen für einen vorhandenen Webserver
- Siehe `docs/ANLEITUNG_SERVER.md`

## Aktuell

Die Basis-Docker-Konfiguration liegt im Projektroot: `docker-compose.yml`
