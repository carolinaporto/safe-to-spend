#!/usr/bin/env bash
# Dump the local dev database to backups/ (gzipped, timestamped).
# Run this before anything risky. Restore with scripts/db_restore.sh <file>.
set -euo pipefail

DB="${1:-safe_to_spend}"
CONTAINER="${DB_CONTAINER:-safe-to-spend-db}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/backups"
mkdir -p "$DIR"

OUT="$DIR/${DB}_$(date +%Y%m%d_%H%M%S).sql.gz"
docker exec "$CONTAINER" pg_dump -U sts -d "$DB" --no-owner | gzip >"$OUT"
echo "wrote $OUT"

# Keep the 20 most recent.
ls -1t "$DIR"/*.sql.gz 2>/dev/null | tail -n +21 | xargs -r rm --
