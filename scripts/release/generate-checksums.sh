#!/usr/bin/env bash
# Generate SHA-256 checksums for release bundle artifacts.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="$(cat "$ROOT/VERSION")"
RELEASE_DIR="${1:-$ROOT/release/v${VERSION}}"

if [[ ! -d "$RELEASE_DIR" ]]; then
  echo "Release directory not found: $RELEASE_DIR" >&2
  exit 1
fi

OUT="$RELEASE_DIR/checksums.sha256"
: > "$OUT"

while IFS= read -r -d '' file; do
  rel="${file#"$RELEASE_DIR"/}"
  if [[ "$rel" == "checksums.sha256" ]]; then
    continue
  fi
  if [[ -f "$file" ]]; then
  hash="$(shasum -a 256 "$file" | awk '{print $1}')"
  echo "$hash  $rel" >> "$OUT"
  fi
done < <(find "$RELEASE_DIR" -type f -print0 | sort -z)

echo "Wrote $OUT ($(wc -l < "$OUT" | tr -d ' ') files)"
