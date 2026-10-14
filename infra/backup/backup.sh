#!/bin/sh
# WareVision DB Backup (Epic 19)
# Verwendung: ./backup.sh [PGHOST] [PGUSER] [PGPASSWORD] [PGDATABASE]
# Oder mit Umgebungsvariablen: PGHOST=postgres ./backup.sh

set -e
BACKUP_DIR="${BACKUP_DIR:-/backups}"
PGHOST="${1:-${PGHOST:-postgres}}"
PGUSER="${2:-${PGUSER:-warevision}}"
PGPASSWORD="${3:-${PGPASSWORD:-warevision}}"
PGDATABASE="${4:-${PGDATABASE:-warevision}}"

export PGHOST PGUSER PGPASSWORD PGDATABASE
mkdir -p "$BACKUP_DIR"
FILE="$BACKUP_DIR/warevision_$(date +%Y%m%d_%H%M%S).dump"
pg_dump -Fc "$PGDATABASE" > "$FILE"
echo "Backup erstellt: $FILE"
echo "Größe: $(du -h "$FILE" | cut -f1)"

# Dateien sichern: Belegarchiv (GoBD-Originale), E-Rechnungs-Originale, Dokumente.
# Ohne diese Dateien sind ausgegebene Belege nach einer Wiederherstellung nicht mehr vorhanden.
UPLOADS_DIR="${UPLOADS_DIR:-/uploads}"
if [ -d "$UPLOADS_DIR" ]; then
  FILES="$BACKUP_DIR/warevision_dateien_$(date +%Y%m%d_%H%M%S).tar.gz"
  tar -czf "$FILES" -C "$UPLOADS_DIR" .
  echo "Dateien gesichert: $FILES"
  echo "Größe: $(du -h "$FILES" | cut -f1)"
else
  echo "WARNUNG: Upload-Verzeichnis $UPLOADS_DIR nicht gefunden – Belegarchiv und Dokumente wurden NICHT gesichert."
fi
