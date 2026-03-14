#!/bin/sh
# WareVision DB Restore (Epic 19.2)
# Verwendung: ./restore.sh <backup.dump> [PGHOST] [PGUSER] [PGPASSWORD] [PGDATABASE]
# Beispiel: ./restore.sh /backups/warevision_20260310_120000.dump

set -e
if [ -z "$1" ]; then
  echo "Verwendung: $0 <backup.dump> [PGHOST] [PGUSER] [PGPASSWORD] [PGDATABASE]"
  echo "Beispiel: $0 /backups/warevision_20260310_120000.dump"
  exit 1
fi

BACKUP_FILE="$1"
PGHOST="${2:-${PGHOST:-postgres}}"
PGUSER="${3:-${PGUSER:-warevision}}"
PGPASSWORD="${4:-${PGPASSWORD:-warevision}}"
PGDATABASE="${5:-${PGDATABASE:-warevision}}"

export PGHOST PGUSER PGPASSWORD PGDATABASE

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Datei nicht gefunden: $BACKUP_FILE"
  exit 1
fi

echo "Warnung: Alle bestehenden Daten werden überschrieben!"
echo "Backup: $BACKUP_FILE -> $PGDATABASE@$PGHOST"
read -r -p "Fortfahren? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
  echo "Abgebrochen."
  exit 0
fi

pg_restore -d "$PGDATABASE" --clean --if-exists "$BACKUP_FILE" || true
echo "Restore abgeschlossen."
