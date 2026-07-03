#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
. "$ROOT/.venv/bin/activate"
export PYTHONPATH="$ROOT/apps/backend/src"
bash "$ROOT/tools/scripts/alembic.sh" upgrade head
exec uvicorn webstudio_backend.app:create_app --factory --host "${API_HOST:-127.0.0.1}" --port "${API_PORT:-8000}" --reload
