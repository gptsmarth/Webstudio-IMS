# Optional installer payload

| File | Purpose |
|------|---------|
| `postgresql-installer.exe` | Optional PostgreSQL 16 silent install if no `postgresql-x64-*` service exists |

**Bundled automatically at release build** (NSSM also vendored in git for CI fallback):

- Embedded Python 3.12 + backend deps → staged under `release/server/staging/runtime/python/`
- NSSM → `release/server/staging/tools/nssm/nssm.exe` (GitHub Releases, then nssm.cc, then `infra/windows/vendor/nssm/win64/nssm.exe`)

See `scripts/release/stage-server-payload.ps1` and [INSTALLER_GUIDE.md](../../../docs/milestones/m12c/INSTALLER_GUIDE.md).
