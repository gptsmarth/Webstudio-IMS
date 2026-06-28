#!/usr/bin/env bash
# Dump the local PostgreSQL database to a timestamped file under backups/.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "ERROR: .env not found. Copy config/env/.env.example to .env first." >&2
  exit 1
fi

# shellcheck disable=SC1091
set -a
source .env
set +a

BACKUP_DIR="$ROOT/backups"
mkdir -p "$BACKUP_DIR"

STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$BACKUP_DIR/webstudio-${POSTGRES_DB:-webstudio_ims}-${STAMP}.sql"

if ! docker compose ps --format json 2>/dev/null | grep -q '"Health":"healthy"'; then
  echo "ERROR: PostgreSQL is not running or not healthy. Start it with: docker compose up -d" >&2
  exit 1
fi

echo "Writing backup to $OUT"
docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-webstudio}" "${POSTGRES_DB:-webstudio_ims}" > "$OUT"

echo "Backup complete ($(wc -c < "$OUT" | tr -d ' ') bytes)"
