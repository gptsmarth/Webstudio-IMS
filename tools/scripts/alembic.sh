#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT/database/migrations"
export PYTHONPATH="$ROOT/apps/backend/src"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
elif command -v python >/dev/null 2>&1; then
  PYTHON="$(command -v python)"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
else
  echo "ERROR: No Python interpreter found. Create a virtualenv at $ROOT/.venv or install python3." >&2
  exit 1
fi

if ! "$PYTHON" -c "import importlib; importlib.import_module('alembic')" >/dev/null 2>&1; then
  echo "ERROR: 'alembic' is not installed for interpreter: $PYTHON" >&2
  echo "From the repo root, install backend dependencies:" >&2
  echo "  pip install -e \"apps/backend[dev]\"" >&2
  echo "Or create a local virtualenv:" >&2
  echo "  python -m venv .venv && source .venv/bin/activate" >&2
  echo "  pip install -e \"apps/backend[dev]\"" >&2
  exit 1
fi

exec "$PYTHON" -m alembic "$@"
