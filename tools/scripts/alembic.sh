#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT/database/migrations"
export PYTHONPATH="$ROOT/apps/backend/src"
alembic "$@"
