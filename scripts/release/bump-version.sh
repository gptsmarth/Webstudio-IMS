#!/usr/bin/env bash
# Bump semver across monorepo packaging manifests via canonical VERSION.json.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="${1:-}"

if [[ -z "$VERSION" ]]; then
  echo "Usage: $0 <semver> [build-number] [release-channel]"
  echo "Example: $0 0.1.0 1 development"
  exit 1
fi

BUILD="${2:-1}"
CHANNEL="${3:-development}"

python3 - "$ROOT" "$VERSION" "$BUILD" "$CHANNEL" <<'PY'
import json
import sys
from pathlib import Path

root, version, build, channel = sys.argv[1:5]
catalog_path = Path(root) / "VERSION.json"
if catalog_path.is_file():
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
else:
    catalog = {
        "schema_version": "1.0.0",
        "product": "WEBSTUDIO IMS",
        "version": version,
        "build_number": int(build),
        "release_channel": channel,
        "release_date": "",
        "git_commit": "",
        "git_short": "",
    }

catalog["version"] = version
catalog["build_number"] = int(build)
catalog["release_channel"] = channel
catalog_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
PY

bash "$ROOT/scripts/release/sync-versions.sh"
echo "Version bumped to $VERSION+$BUILD ($CHANNEL)"
