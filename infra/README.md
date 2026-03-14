# Infrastruktur (infra)

Dieser Ordner enthält Infrastruktur-Konfigurationen für WareVision.

## Backup (Epic 19)

- `backup/backup.sh` – PostgreSQL-Dump-Script
- `backup/restore.sh` – Restore-Script
- Siehe `docs/ANLEITUNG_BACKUP.md` für Verwendung

## Geplante Inhalte

- Docker Compose (Produktion)
- Reverse Proxy (Caddy/Nginx)
- CI/CD (GitLab)
- Monitoring-Konfiguration

## Aktuell

Die Basis-Docker-Konfiguration liegt im Projektroot: `docker-compose.yml`
