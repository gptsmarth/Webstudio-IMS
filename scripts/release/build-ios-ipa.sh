#!/usr/bin/env bash
# Build a signed IPA when export options are provided on a provisioned Mac.
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

flutter pub get --enforce-lockfile
dart run flutter_launcher_icons
dart run flutter_native_splash:create

echo "[release] Installing CocoaPods dependencies..."
cd ios
pod install --repo-update
cd ..

mkdir -p "$RELEASE_DIR"
export_options="${WEBSTUDIO_IOS_EXPORT_OPTIONS_PLIST:-}"
if [[ -n "$export_options" ]]; then
  plutil -lint "$export_options"
  flutter build ipa --release --no-pub --export-options-plist "$export_options"
  shopt -s nullglob
  ipas=(build/ios/ipa/*.ipa)
  if [[ "${#ipas[@]}" -ne 1 ]]; then
    echo "[release] Expected one signed IPA in build/ios/ipa." >&2
    exit 1
  fi
  cp "${ipas[0]}" "$RELEASE_DIR/../WEBSTUDIO IMS.ipa"
  echo "[release] Signed IPA exported. Use the distribution channel in ExportOptions.plist."
else
  flutter build ipa --release --no-pub --no-codesign
  ditto build/ios/archive/Runner.xcarchive "$RELEASE_DIR/WEBSTUDIO-IMS-unsigned.xcarchive"
  echo "[release] Unsigned build validation archive. Device installation requires a signed IPA."
fi
