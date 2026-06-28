#!/usr/bin/env bash
# Wipe PostgreSQL data volume, recreate container, and apply all migrations.
# DESTRUCTIVE — creates a backup first when PostgreSQL is running.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [[ "${I_UNDERSTAND_DATA_WILL_BE_DELETED:-}" != "1" ]]; then
  echo "WARNING: fresh-dev.sh deletes ALL local database data (docker compose down -v)." >&2
  echo "Your login, inventory, and setup will be lost unless you have a backup." >&2
  echo "" >&2
  echo "To continue, run:" >&2
  echo "  I_UNDERSTAND_DATA_WILL_BE_DELETED=1 bash tools/scripts/fresh-dev.sh" >&2
  exit 1
fi

if docker compose ps --format json 2>/dev/null | grep -q '"Health":"healthy"'; then
  echo "Creating safety backup before wipe..."
  bash "$ROOT/tools/scripts/backup-db.sh" || echo "Backup skipped (non-fatal)."
else
  echo "PostgreSQL not healthy — skipping backup."
fi

echo "Stopping PostgreSQL and removing data volume..."
docker compose down -v

echo "Starting fresh PostgreSQL..."
docker compose up -d

echo "Waiting for PostgreSQL to become healthy..."
for _ in $(seq 1 30); do
  if docker compose ps --format json 2>/dev/null | grep -q '"Health":"healthy"'; then
    break
  fi
  sleep 2
done

if ! docker compose ps --format json 2>/dev/null | grep -q '"Health":"healthy"'; then
  echo "ERROR: PostgreSQL did not become healthy in time." >&2
  docker compose ps
  exit 1
fi

echo "Applying database migrations..."
# shellcheck source=/dev/null
. "$ROOT/.venv/bin/activate"
bash "$ROOT/tools/scripts/alembic.sh" upgrade head

echo ""
echo "Fresh database ready."
echo "  system_initialized=false (Setup Wizard will appear automatically)"
echo ""
echo "Next:"
echo "  Terminal 1: bash tools/scripts/dev-backend.sh"
echo "  Terminal 2: pnpm desktop:dev"
echo ""
echo "Restore from backup: see docs/development/LOCAL_DEVELOPMENT.md"
