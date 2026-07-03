# Optional installer payload

| File | Purpose |
|------|---------|
| `postgresql-installer.exe` | Optional PostgreSQL 16 silent install if no `postgresql-x64-*` service exists |

**Bundled automatically at release build** (not stored in git):

- Embedded Python 3.12 + backend deps → staged under `release/server/staging/runtime/python/`
- NSSM → `release/server/staging/tools/nssm/nssm.exe`

See `scripts/release/stage-server-payload.ps1` and [INSTALLER_GUIDE.md](../../../docs/milestones/m12c/INSTALLER_GUIDE.md).
