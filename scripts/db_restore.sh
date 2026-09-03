#!/usr/bin/env bash
# Restore a dump made by scripts/db_backup.sh into the local dev database.
# Usage: scripts/db_restore.sh backups/safe_to_spend_YYYYMMDD_HHMMSS.sql.gz
set -euo pipefail

FILE="${1:?usage: db_restore.sh <backups/xxx.sql.gz> [dbname]}"
DB="${2:-safe_to_spend}"
CONTAINER="${DB_CONTAINER:-safe-to-spend-db}"

[ -f "$FILE" ] || { echo "no such file: $FILE" >&2; exit 1; }

read -rp "This DROPs and recreates '$DB' from $FILE. Type 'restore' to confirm: " ok
[ "$ok" = "restore" ] || { echo "aborted"; exit 1; }

docker exec "$CONTAINER" psql -U sts -d postgres -c \
  "DROP DATABASE IF EXISTS $DB; CREATE DATABASE $DB OWNER sts;"
gunzip -c "$FILE" | docker exec -i "$CONTAINER" psql -U sts -d "$DB" -q
echo "restored $DB from $FILE"
