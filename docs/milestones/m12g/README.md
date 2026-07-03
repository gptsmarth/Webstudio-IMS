---
Title: Milestone 12G — Release Engineering
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
---

# Milestone 12G — Release Engineering

Production release preparation: manifests, checksums, notes, migrations, environment profiles, logging, and release folder layout.

## Deliverables

| Artifact | Location |
|----------|----------|
| Version manifest generator | `scripts/release/lib/generate_manifest.py` |
| Checksums | `scripts/release/generate-checksums.sh` |
| Release notes | `scripts/release/generate-release-notes.sh` |
| Migration packaging | `scripts/release/package-migrations.sh` |
| Full bundle assembly | `scripts/release/prepare-release.sh` → `pnpm release:prepare` |
| Environment profiles | `config/env/.env.{development,testing,staging,production}` |
| Production logging | `config/logging/production-logging.md` + `WEBSTUDIO_LOG_DIR` |
| Crash logging | `config/logging/crash-logging.md` + `WEBSTUDIO_CRASH_LOG_DIR` + Electron `crashReporter` |
| Release folder structure | `release/README.md`, `release/STRUCTURE.md` |
| CI | `.github/workflows/release.yml` → `release-bundle` job |
| Engineering report | [RELEASE_ENGINEERING_REPORT.md](./RELEASE_ENGINEERING_REPORT.md) |

## Quick start

```bash
pnpm release:prepare
ls release/v0.1.0/
```
