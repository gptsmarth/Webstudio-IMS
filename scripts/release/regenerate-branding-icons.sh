#!/usr/bin/env bash
# Regenerate platform icons (ico, icns, Flutter sync) from canonical icon.png.
# Optional: --from-svg renders icon.png from icon.svg first.
# Optional: --source <file> copies a new master PNG (1024×1024 recommended) then builds.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WEBSTUDIO="$ROOT/apps/desktop/public/assets/webstudio"
SVG="$WEBSTUDIO/icon.svg"
MASTER="$WEBSTUDIO/icon.png"
FROM_SVG=false
SOURCE_FILE=""

usage() {
  echo "Usage: $0 [--from-svg] [--source <path-to-png>]" >&2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --from-svg)
      FROM_SVG=true
      shift
      ;;
    --source)
      SOURCE_FILE="${2:-}"
      if [[ -z "$SOURCE_FILE" ]]; then
        usage
        exit 1
      fi
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -n "$SOURCE_FILE" ]]; then
  if [[ ! -f "$SOURCE_FILE" ]]; then
    echo "Source file not found: $SOURCE_FILE" >&2
    exit 1
  fi
  echo "[branding] Installing master icon from $SOURCE_FILE..."
  sips -s format png "$SOURCE_FILE" --out "$MASTER" >/dev/null
  sips -z 1024 1024 "$MASTER" --out "$MASTER" >/dev/null
fi

if $FROM_SVG; then
  if [[ ! -f "$SVG" ]]; then
    echo "Missing source vector icon: $SVG" >&2
    exit 1
  fi
  echo "[branding] Rendering icon.png from icon.svg..."
  (
    cd "$WEBSTUDIO"
    npx --yes @resvg/resvg-js-cli icon.svg icon.png --fit-width 1024 --fit-height 1024
  )
fi

if [[ ! -f "$MASTER" ]]; then
  echo "Missing master icon: $MASTER (use --source or --from-svg)" >&2
  exit 1
fi

if ! file -b "$MASTER" | grep -q "PNG image"; then
  echo "Master icon is not a PNG: $MASTER" >&2
  exit 1
fi

TMP_ICO="$(mktemp -d)"
trap 'rm -rf "$TMP_ICO"' EXIT

echo "[branding] Building multi-size icon.ico from icon.png..."
for size in 16 24 32 48 64 128 256; do
  sips -z "$size" "$size" "$MASTER" --out "$TMP_ICO/icon_${size}.png" >/dev/null
done
npx --yes png-to-ico "$TMP_ICO"/icon_*.png >"$WEBSTUDIO/icon.ico"

if [[ "$(uname -s)" == "Darwin" ]]; then
  echo "[branding] Building icon.icns (macOS iconutil)..."
  ICONSET="$WEBSTUDIO/icon.iconset"
  rm -rf "$ICONSET"
  mkdir -p "$ICONSET"
  sips -z 16 16 "$MASTER" --out "$ICONSET/icon_16x16.png" >/dev/null
  sips -z 32 32 "$MASTER" --out "$ICONSET/icon_16x16@2x.png" >/dev/null
  sips -z 32 32 "$MASTER" --out "$ICONSET/icon_32x32.png" >/dev/null
  sips -z 64 64 "$MASTER" --out "$ICONSET/icon_32x32@2x.png" >/dev/null
  sips -z 128 128 "$MASTER" --out "$ICONSET/icon_128x128.png" >/dev/null
  sips -z 256 256 "$MASTER" --out "$ICONSET/icon_128x128@2x.png" >/dev/null
  sips -z 256 256 "$MASTER" --out "$ICONSET/icon_256x256.png" >/dev/null
  sips -z 512 512 "$MASTER" --out "$ICONSET/icon_256x256@2x.png" >/dev/null
  sips -z 512 512 "$MASTER" --out "$ICONSET/icon_512x512.png" >/dev/null
  cp "$MASTER" "$ICONSET/icon_512x512@2x.png"
  iconutil -c icns "$ICONSET" -o "$WEBSTUDIO/icon.icns"
else
  echo "[branding] Skipping icon.icns (requires macOS iconutil). Run on macOS before macOS/desktop release."
fi

bash "$ROOT/scripts/release/validate-branding-icons.sh"
bash "$ROOT/scripts/release/sync-branding-assets.sh"

echo "[branding] Regenerated icon.ico and icon.icns from $MASTER"
