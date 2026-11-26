# Server installer dependencies

For automatic setup on a fresh server, the installer downloads the pinned
PostgreSQL package from EDB and checks its SHA-256. For offline installation,
prepare PostgreSQL beforehand and select the manual database option in Setup.

**Bundled automatically at release build** (NSSM also vendored in git for CI fallback):

- Embedded Python 3.12 + backend deps → staged under `release/server/staging/runtime/python/`
- NSSM → `release/server/staging/tools/nssm/nssm.exe` (GitHub Releases, then nssm.cc, then `infra/windows/vendor/nssm/win64/nssm.exe`)

See `scripts/release/stage-server-payload.ps1` and [INSTALLER_GUIDE.md](../../../../docs/milestones/m12c/INSTALLER_GUIDE.md).
