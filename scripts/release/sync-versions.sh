#!/usr/bin/env bash
# Propagate VERSION.json across backend, desktop, Flutter, installer, and release metadata.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
python3 "$ROOT/scripts/release/lib/sync_versions.py" "$@"
