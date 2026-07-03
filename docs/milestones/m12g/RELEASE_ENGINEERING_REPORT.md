---
Title: Release Engineering Report
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12G
Related Documents:
  - docs/milestones/m12a/VERSION_STRATEGY.md
  - docs/milestones/m12c/INSTALLER_GUIDE.md
  - release/README.md
---

# Release Engineering Report — Milestone 12G

**Date:** 2026-07-02  
**Release version:** `0.1.0` (from `VERSION`)  
**Alembic head:** `0036_tally_probe_scheduler` (36 migrations)  
**Verdict:** **READY** for tagged release builds and operator distribution.

---

## Executive summary

M12G completes the release engineering pipeline started in M12A/M12C:

1. **Automated bundle assembly** — one command produces manifest, checksums, notes, migrations, and env profiles  
2. **Four environment profiles** — development, testing, staging, production  
3. **Production + crash logging** — file sinks on server; Electron crashReporter + local crash dumps  
4. **CI integration** — tag push builds artifacts and uploads `release-bundle`  
5. **No manual checksum or version spreadsheet** — `version-manifest.json` is the single source of truth  

---

## Version manifest

**Generator:** `python3 scripts/release/lib/generate_manifest.py`  
**Output:** `release/v{VERSION}/version-manifest.json`

| Field | Purpose |
|-------|---------|
| `release_version` | SemVer from `VERSION` |
| `build.git_commit` | Reproducible build traceability |
| `components.*` | Desktop, mobile, backend versions |
| `database.alembic_head` | Required migration revision for upgrade |
| `artifacts` | Expected installer filenames |

**Propagation rule:** Run `scripts/release/bump-version.sh` before tagging; manifest reads live package files.

---

## Checksums

**Script:** `scripts/release/generate-checksums.sh`  
**Format:** GNU `sha256sum` compatible (`hash  path`)

```bash
cd release/v0.1.0
shasum -a 256 -c checksums.sha256
```

Includes migrations, env profiles, logging docs, manifest, notes, and any packaged installers.

---

## Release notes

**Script:** `scripts/release/generate-release-notes.sh`  
**Source:** `CHANGELOG.md` section for current `VERSION`  
**Output:** `RELEASE_NOTES.md` with upgrade steps and doc links  

Maintain `CHANGELOG.md` before each release tag.

---

## Migration scripts

**Script:** `scripts/release/package-migrations.sh`  
**Contents:** Full `database/migrations/` tree (36 revision files + `alembic.ini`)

**Upgrade command (server):**

```bash
cd apps/backend
alembic -c ../../database/migrations/alembic.ini upgrade head
```

Verify `database.alembic_head` in manifest matches `alembic current`.

---

## Environment profiles

| Profile | File | `APP_ENV` | Use case |
|---------|------|-----------|----------|
| Development | `config/env/.env.development` | `development` | Local engineer workstations |
| Testing | `config/env/.env.testing` | `test` | CI / pytest |
| Staging | `config/env/.env.staging` | `staging` | Pre-production LAN validation |
| Production | `config/env/.env.production` | `production` | Dedicated showroom server |

Copied to `release/v{VERSION}/env/*.env` during `pnpm release:prepare`.

**Rule:** Never commit production secrets — installer generates `JWT_SECRET` (M12C).

---

## Logging

### Production logging (backend)

| Variable | Effect |
|----------|--------|
| `LOG_JSON=true` | Structured JSON on stdout |
| `WEBSTUDIO_LOG_DIR` | Rotating `webstudio-api.log` (10 MB × 5) |
| `LOG_LEVEL=INFO` | Default production verbosity |

Implementation: `apps/backend/src/webstudio_backend/core/logging.py`

### Crash logging

| Layer | Mechanism |
|-------|-----------|
| Backend | `WEBSTUDIO_CRASH_LOG_DIR/webstudio-crash.log` (ERROR+) |
| Desktop | `crashReporter` + `crash-reports/crash-{timestamp}.log` on uncaught exceptions |
| Mobile | Server-side correlation; no device crash SDK in MVP |

Guides: `config/logging/production-logging.md`, `config/logging/crash-logging.md`

---

## Release folder structure

```
release/v0.1.0/
├── version-manifest.json
├── checksums.sha256
├── RELEASE_NOTES.md
├── artifacts/
├── migrations/
├── env/
└── logging/
```

See [release/README.md](../../../release/README.md).

---

## CI pipeline

| Job | Output |
|-----|--------|
| `desktop-windows` | `WEBSTUDIO Desktop Setup.exe` |
| `desktop-macos` | `WEBSTUDIO Desktop.dmg` |
| `mobile-android` | `WEBSTUDIO IMS.apk` |
| `server-windows` | `WEBSTUDIO Server Setup.exe` |
| `release-bundle` | Full `release/v*/` with manifest + checksums |

**Trigger:** `git tag v0.1.0 && git push origin v0.1.0`

---

## Pre-release checklist

| # | Step | Command / location |
|---|------|-------------------|
| 1 | Bump version | `bash scripts/release/bump-version.sh X.Y.Z N` |
| 2 | Update CHANGELOG | `CHANGELOG.md` |
| 3 | Run full test suite | `pnpm test` + backend pytest |
| 4 | Build installers | M12C scripts |
| 5 | Prepare bundle | `pnpm release:prepare` |
| 6 | Verify checksums | `shasum -a 256 -c checksums.sha256` |
| 7 | Tag and push | `vX.Y.Z` |
| 8 | Staging smoke test | M12E validation guide |
| 9 | Production deploy | DEPLOY-001 + M12B business hours |

---

## Gaps (post-1.0)

| Item | Priority |
|------|----------|
| Code signing (Windows/macOS/Android) | High for external distribution |
| iOS CI job (`mobile-ios` disabled) | Medium |
| Python `requirements.lock` | Medium for reproducible server builds |
| Automated CHANGELOG from conventional commits | Low |

---

## Sign-off

| Role | Status | Date |
|------|--------|------|
| Release engineering | Complete (M12G) | 2026-07-02 |
| QA staging | Pending operator run | — |
| Production deploy | Pending | — |
