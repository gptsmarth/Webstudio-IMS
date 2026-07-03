#!/usr/bin/env bash
# Fail fast when branding raster files are placeholders (e.g. SVG renamed as .ico/.png).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WEBSTUDIO="$ROOT/apps/desktop/public/assets/webstudio"

check_file() {
  local path="$1"
  local expected="$2"
  if [[ ! -f "$path" ]]; then
    echo "Missing branding asset: $path" >&2
    exit 1
  fi
  local actual
  actual="$(file -b "$path")"
  if [[ "$actual" != *"$expected"* ]]; then
    echo "Invalid branding asset: $path" >&2
    echo "  expected type hint: $expected" >&2
    echo "  actual: $actual" >&2
    exit 1
  fi
  echo "[branding] OK $path"
}

check_file "$WEBSTUDIO/icon.ico" "MS Windows icon"
check_file "$WEBSTUDIO/icon.icns" "Mac OS X icon"
check_file "$WEBSTUDIO/icon.png" "PNG image"

# Reject generic placeholder PNGs (real WEBSTUDIO mark from icon.svg is ~80KB+ at 1024²).
png_bytes="$(wc -c <"$WEBSTUDIO/icon.png" | tr -d ' ')"
if [[ "$png_bytes" -lt 30000 ]]; then
  echo "icon.png looks like a placeholder (${png_bytes} bytes). Run scripts/release/regenerate-branding-icons.sh" >&2
  exit 1
fi
