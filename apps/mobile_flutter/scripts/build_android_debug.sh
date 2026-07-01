#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v flutter >/dev/null 2>&1; then
  echo "Flutter SDK required."
  exit 1
fi

if [[ ! -d android ]]; then
  bash scripts/setup_platforms.sh
fi

flutter build apk --debug
echo "Debug APK built."
