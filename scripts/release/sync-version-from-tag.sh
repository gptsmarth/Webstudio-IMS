#!/usr/bin/env bash
# Sync canonical VERSION.json from the git tag (CI: GITHUB_REF_NAME=vX.Y.Z).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TAG="${1:-${GITHUB_REF_NAME:-}}"

if [[ -z "$TAG" ]]; then
  echo "Usage: sync-version-from-tag.sh <tag-or-vX.Y.Z>" >&2
  exit 1
fi

VERSION="${TAG#v}"
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+ ]]; then
  echo "Invalid release tag version: $TAG (expected vMAJOR.MINOR.PATCH)" >&2
  exit 1
fi

BUILD="${WEBSTUDIO_BUILD_NUMBER:-${GITHUB_RUN_NUMBER:-1}}"
CHANNEL="${WEBSTUDIO_RELEASE_CHANNEL:-stable}"
GIT_COMMIT="${GITHUB_SHA:-$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || true)}"
GIT_SHORT="${GIT_COMMIT:0:7}"
RELEASE_DATE="$(date -u +%F)"

python3 - "$ROOT" "$VERSION" "$BUILD" "$CHANNEL" "$GIT_COMMIT" "$GIT_SHORT" "$RELEASE_DATE" <<'PY'
import json
import sys
from pathlib import Path

root, version, build, channel, git_commit, git_short, release_date = sys.argv[1:8]
catalog_path = Path(root) / "VERSION.json"
catalog = {
    "schema_version": "1.0.0",
    "product": "WEBSTUDIO IMS",
    "version": version,
    "build_number": int(build),
    "release_channel": channel,
    "release_date": release_date,
    "git_commit": git_commit,
    "git_short": git_short,
}
if catalog_path.is_file():
    existing = json.loads(catalog_path.read_text(encoding="utf-8"))
    existing.update(catalog)
    catalog = existing
catalog_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
PY

bash "$ROOT/scripts/release/sync-versions.sh"
echo "[release] VERSION.json set to $VERSION+$BUILD from tag $TAG"
