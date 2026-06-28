#!/usr/bin/env bash
# Create webstudio_test if missing (safe to run repeatedly).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$ROOT/.env"
  set +a
fi

POSTGRES_USER="${POSTGRES_USER:-webstudio_app}"
POSTGRES_DB="${POSTGRES_DB:-webstudio_dev}"
TEST_DB="${WEBSTUDIO_TEST_DB:-webstudio_test}"

if docker compose ps --format json 2>/dev/null | grep -q '"Health":"healthy"'; then
  EXISTS="$(docker compose exec -T postgres psql -U "$POSTGRES_USER" -d postgres -tAc \
    "SELECT 1 FROM pg_database WHERE datname = '${TEST_DB}'" 2>/dev/null | tr -d '[:space:]' || true)"
  if [[ "$EXISTS" != "1" ]]; then
    echo "Creating PostgreSQL database: ${TEST_DB}"
    docker compose exec -T postgres psql -U "$POSTGRES_USER" -d postgres -c \
      "CREATE DATABASE ${TEST_DB} OWNER ${POSTGRES_USER};"
  fi
else
  echo "PostgreSQL container not healthy — skipping test database creation." >&2
fi
