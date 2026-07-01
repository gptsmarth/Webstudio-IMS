#!/usr/bin/env bash
# Generates android/ and ios/ folders when Flutter SDK is available.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v flutter >/dev/null 2>&1; then
  echo "Flutter SDK not found. Install from https://docs.flutter.dev/get-started/install"
  exit 1
fi

if [[ -d android && -d ios ]]; then
  echo "Platform folders already exist. Run 'flutter pub get' only."
  flutter pub get
  exit 0
fi

flutter create --org com.webstudio --project-name webstudio_ims .
flutter pub get
echo "Platform scaffolding complete."
