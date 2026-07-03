# WEBSTUDIO IMS — Release Folder Structure (M12G)

Generated release bundles live under `release/v{VERSION}/`.

```
release/
├── README.md                    # This overview
├── STRUCTURE.md                 # Copied into each version bundle
├── mobile/                      # Local mobile build outputs (M12C)
│   └── WEBSTUDIO IMS.apk
├── server/                      # Server installer output
│   └── WEBSTUDIO Server Setup.exe
└── v0.1.0/                      # Prepared bundle (example)
    ├── version-manifest.json    # Component versions, git commit, Alembic head
    ├── checksums.sha256         # SHA-256 for all files in bundle
    ├── RELEASE_NOTES.md         # Operator-facing release notes
    ├── STRUCTURE.md             # Folder layout reference
    ├── artifacts/               # Installers (when built)
    │   ├── WEBSTUDIO-Desktop-Setup.exe
    │   ├── WEBSTUDIO-Desktop.dmg
    │   ├── WEBSTUDIO-IMS.apk
    │   └── WEBSTUDIO-Server-Setup.exe
    ├── migrations/              # Alembic scripts for upgrade
    │   ├── alembic.ini
    │   ├── env.py
    │   ├── script.py.mako
    │   ├── versions/*.py
    │   └── README.md
    ├── env/                     # Environment profiles
    │   ├── .env.example
    │   ├── development.env
    │   ├── testing.env
    │   ├── staging.env
    │   └── production.env
    └── logging/                 # Logging operator guides
        ├── production-logging.md
        ├── crash-logging.md
        └── logrotate-webstudio.conf.example
```

## Prepare a release

```bash
# Bump version (optional)
bash scripts/release/bump-version.sh 0.1.0 1

# Build artifacts (optional — see docs/milestones/m12c/INSTALLER_GUIDE.md)
pnpm desktop:package:win
pnpm release:android

# Assemble bundle
pnpm release:prepare
```

## Verify checksums

```bash
cd release/v0.1.0
shasum -a 256 -c checksums.sha256
```

## CI

Tag `v*.*.*` triggers `.github/workflows/release.yml` — artifacts uploaded to GitHub Actions, then `release-bundle` job assembles manifest and checksums.
