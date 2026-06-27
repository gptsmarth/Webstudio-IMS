#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PYTHONPATH="$ROOT/apps/backend/src"
python -m webstudio_backend.infrastructure.database.seed.reference_data
