#!/usr/bin/env bash
# Build release-signed WEBSTUDIO IMS.apk (APK only — no AAB).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FLUTTER_DIR="$ROOT/apps/mobile_flutter"
RELEASE_DIR="$ROOT/release/mobile"

bash "$ROOT/scripts/release/sync-branding-assets.sh"

cd "$FLUTTER_DIR"
flutter pub get
dart run flutter_launcher_icons
dart run flutter_native_splash:create

echo "[release] Building Android APK..."
DART_DEFINES=()
# Optional: WEBSTUDIO_DEFAULT_API_URL=http://192.168.29.100:8000 pnpm release:android
if [[ -n "${WEBSTUDIO_DEFAULT_API_URL:-}" ]]; then
  DART_DEFINES+=(--dart-define="WEBSTUDIO_DEFAULT_API_URL=${WEBSTUDIO_DEFAULT_API_URL}")
  echo "[release] Default API URL: ${WEBSTUDIO_DEFAULT_API_URL}"
fi
if (( ${#DART_DEFINES[@]} )); then
  flutter build apk --release "${DART_DEFINES[@]}"
else
  flutter build apk --release
fi

mkdir -p "$RELEASE_DIR"
APK_SRC="$FLUTTER_DIR/build/app/outputs/flutter-apk/app-release.apk"
APK_DST="$RELEASE_DIR/WEBSTUDIO IMS.apk"

if [[ ! -f "$APK_SRC" ]]; then
  echo "Expected APK not found at $APK_SRC" >&2
  exit 1
fi

cp "$APK_SRC" "$APK_DST"
echo "[release] Output: $APK_DST"
