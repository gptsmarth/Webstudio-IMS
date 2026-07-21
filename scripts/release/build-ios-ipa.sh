#!/usr/bin/env bash
# Configure Flutter iOS project and build Release IPA (no App Store assets).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FLUTTER_DIR="$ROOT/apps/mobile_flutter"
RELEASE_DIR="$ROOT/release/mobile/ios"

bash "$ROOT/scripts/release/sync-branding-assets.sh"

# Stable temp dir — GitHub Actions + Flutter SPM previously failed with:
#   The file "manifest.swift" couldn't be saved in TemporaryDirectory.*
# Even with SPM disabled, keep a project-local TMPDIR for Xcode tooling.
export TMPDIR="${TMPDIR:-$ROOT/.tmp/ios-build}"
mkdir -p "$TMPDIR"
# Avoid inherited GIT_CONFIG_* overrides that can break package/git resolution.
export GIT_CONFIG_COUNT=0

cd "$FLUTTER_DIR"

# Project pubspec disables SPM; reinforce for the CI Flutter install.
flutter config --no-enable-swift-package-manager >/dev/null

flutter pub get
dart run flutter_launcher_icons
dart run flutter_native_splash:create

echo "[release] Installing CocoaPods dependencies..."
cd ios
pod install --repo-update
cd ..

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
