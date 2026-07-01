#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v flutter >/dev/null 2>&1; then
  echo "Flutter SDK required. Install: https://docs.flutter.dev/get-started/install"
  exit 1
fi

flutter pub get
flutter analyze
flutter test
echo "Lint and tests passed."
