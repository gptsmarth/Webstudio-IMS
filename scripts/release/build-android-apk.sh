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
flutter build apk --release

mkdir -p "$RELEASE_DIR"
APK_SRC="$FLUTTER_DIR/build/app/outputs/flutter-apk/app-release.apk"
APK_DST="$RELEASE_DIR/WEBSTUDIO IMS.apk"

if [[ ! -f "$APK_SRC" ]]; then
  echo "Expected APK not found at $APK_SRC" >&2
  exit 1
fi

cp "$APK_SRC" "$APK_DST"
echo "[release] Output: $APK_DST"
