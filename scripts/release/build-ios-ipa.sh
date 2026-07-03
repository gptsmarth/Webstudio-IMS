#!/usr/bin/env bash
# Configure Flutter iOS project and build Release IPA (no App Store assets).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FLUTTER_DIR="$ROOT/apps/mobile_flutter"
RELEASE_DIR="$ROOT/release/mobile/ios"

bash "$ROOT/scripts/release/sync-branding-assets.sh"

cd "$FLUTTER_DIR"
flutter pub get
dart run flutter_launcher_icons
dart run flutter_native_splash:create

echo "[release] Building iOS Release (no codesign)..."
flutter build ios --release --no-codesign

mkdir -p "$RELEASE_DIR"

if command -v xcodebuild >/dev/null 2>&1; then
  echo "[release] Archive with Xcode (requires DEVELOPMENT_TEAM in ios/Release.xcconfig or env)..."
  cd ios
  xcodebuild \
    -workspace Runner.xcworkspace \
    -scheme Runner \
    -configuration Release \
    -archivePath "$RELEASE_DIR/WEBSTUDIO-IMS.xcarchive" \
    archive \
    CODE_SIGNING_ALLOWED="${CODE_SIGNING_ALLOWED:-NO}"
  if [[ -f ExportOptions.plist ]] && [[ "${CODE_SIGNING_ALLOWED:-NO}" == "YES" ]]; then
    xcodebuild \
      -exportArchive \
      -archivePath "$RELEASE_DIR/WEBSTUDIO-IMS.xcarchive" \
      -exportPath "$RELEASE_DIR" \
      -exportOptionsPlist ExportOptions.plist
  fi
  echo "[release] iOS archive: $RELEASE_DIR/WEBSTUDIO-IMS.xcarchive"
else
  echo "[release] xcodebuild not available — open ios/Runner.xcworkspace in Xcode to Archive."
fi

echo "[release] See docs/milestones/m12c/INSTALLER_GUIDE.md for IPA export steps."
