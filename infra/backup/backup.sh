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
