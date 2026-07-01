#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v flutter >/dev/null 2>&1; then
  echo "Flutter SDK required. Install: https://docs.flutter.dev/get-started/install"
  exit 1
fi

echo "=== WEBSTUDIO IMS Mobile QA ==="
flutter pub get

echo ""
echo "--- Static analysis ---"
flutter analyze

echo ""
echo "--- Unit + QA tests ---"
flutter test --reporter expanded

echo ""
echo "--- QA suite only ---"
flutter test test/qa --reporter compact

echo ""
echo "Mobile QA passed."
