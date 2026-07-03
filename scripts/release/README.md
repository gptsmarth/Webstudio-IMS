# Release build scripts (M12C / M12G)

See [docs/milestones/m12c/INSTALLER_GUIDE.md](../docs/milestones/m12c/INSTALLER_GUIDE.md) and [docs/milestones/m12g/RELEASE_ENGINEERING_REPORT.md](../docs/milestones/m12g/RELEASE_ENGINEERING_REPORT.md).

## Build installers

```bash
pnpm release:sync-branding
pnpm desktop:package:win    # Windows
pnpm desktop:package:mac    # macOS
pnpm release:android
pnpm release:backend
powershell scripts/release/build-server-setup.ps1
```

## Enterprise CI (tag push)

Push `v*.*.*` tag → `.github/workflows/release.yml` runs quality gate, builds all artifacts, generates manifest/checksums/notes, uploads to GitHub Release. **Does not deploy.**

See [docs/milestones/m13/CICD_PIPELINE_REPORT.md](../docs/milestones/m13/CICD_PIPELINE_REPORT.md).

## Prepare release bundle (M12G)

```bash
pnpm release:prepare
```

Outputs `release/v{VERSION}/` with:

- `version-manifest.json`
- `checksums.sha256`
- `RELEASE_NOTES.md`
- `migrations/`
- `env/` (development, testing, staging, production)
- `logging/`
- `artifacts/` (when installers were built)

## Version bump

```bash
bash scripts/release/bump-version.sh 0.2.0 2
```
