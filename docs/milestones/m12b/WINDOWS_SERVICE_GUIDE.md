---
Title: Windows Service Guide — WEBSTUDIO Server
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12B
Related Documents:
  - docs/milestones/m12b/DEPLOYMENT_GUIDE.md
  - docs/milestones/m12b/BUSINESS_HOURS_DEPLOYMENT_GUIDE.md
  - infra/windows/install-webstudio-service.ps1
---

# Windows Service Guide — WEBSTUDIO Server Service

**Service name:** `WEBSTUDIO Server`  
**Display name:** WEBSTUDIO Server Service  
**Startup type:** Automatic (Delayed Start)

---

## Overview

The WEBSTUDIO API runs as a Windows service on a dedicated **Windows 11 Pro** server PC. NSSM (Non-Sucking Service Manager) wraps the Python virtual environment and `webstudio_backend.main` entrypoint.

On boot the service:

1. Waits for Windows delayed-auto-start phase  
2. Assumes PostgreSQL is started (via dependency script or manual `ensure-postgresql.ps1`)  
3. Runs startup orchestration (DB, storage, config, AI, Tally checks)  
4. Restores scheduler runtime state from PostgreSQL  
5. Resumes Tally, backup, notification, audit retention, and maintenance schedulers **from persisted next-run times**  
6. Accepts HTTPS/API traffic when `/health/ready` reports ready  

On shutdown the service:

1. Stops accepting new scheduler work  
2. Waits for in-flight Tally sync (up to `WEBSTUDIO_GRACEFUL_SHUTDOWN_SECONDS`)  
3. Checkpoints Tally sync history if interrupted  
4. Persists scheduler state to PostgreSQL  
5. Flushes logs  
6. Closes database connections  

---

## Prerequisites

| Item | Requirement |
|------|-------------|
| OS | Windows 11 Pro |
| PostgreSQL | 16.x Windows service (default name `postgresql-x64-16`) |
| Python | 3.12+ venv at `D:\WEBSTUDIO-IMS\venv` |
| NSSM | `D:\WEBSTUDIO-IMS\tools\nssm\nssm.exe` |
| Install root | `D:\WEBSTUDIO-IMS\` (logs, backups, certs) |

---

## Installation

Run **elevated PowerShell**:

```powershell
cd D:\WEBSTUDIO-IMS\repo\infra\windows
.\install-webstudio-service.ps1 `
  -InstallRoot "D:\WEBSTUDIO-IMS" `
  -PostgresServiceName "postgresql-x64-16"
```

The script:

- Verifies/starts PostgreSQL  
- Registers the service with NSSM  
- Sets **Automatic (Delayed Start)**  
- Configures log rotation under `D:\WEBSTUDIO-IMS\logs\`  
- Runs `alembic upgrade head`  
- Applies service recovery (restart on failure)  
- Starts the service  

---

## Service configuration

| Setting | Value |
|---------|--------|
| Executable | `{InstallRoot}\venv\Scripts\python.exe` |
| Arguments | `-m webstudio_backend.main` |
| Working directory | `{InstallRoot}\apps\backend` |
| Startup | `SERVICE_DELAYED_AUTO_START` |
| Exit action | Restart after 5 s |
| Recovery | 3 restarts / 60 s interval; fail count reset 24 h |

Environment variables (minimum):

```
APP_ENV=production
WEBSTUDIO_DATA_ROOT=D:\WEBSTUDIO-IMS
WEBSTUDIO_TALLY_SCHEDULER=1
WEBSTUDIO_BACKUP_SCHEDULER=1
WEBSTUDIO_NOTIFICATION_SCHEDULER=1
WEBSTUDIO_MAINTENANCE_SCHEDULER=1
JWT_SECRET=<32+ bytes>
DATABASE_URL=postgresql+asyncpg://...
```

**Product images:** keep `WEBSTUDIO_DATA_ROOT` unquoted and equal to the install root.
Files are stored at `{WEBSTUDIO_DATA_ROOT}\assets\product-images\`. Database URLs must stay
`/assets/product-images/{uuid}.ext` (never a Windows path). Desktop and mobile both load
images through `GET /api/v1/product-images/proxy`.

Copy secrets from `config/env/.env.example` into `{InstallRoot}\config\env\.env` — Pydantic Settings loads this file at runtime.

---

## Manual service commands

```powershell
Start-Service "WEBSTUDIO Server"
Stop-Service "WEBSTUDIO Server"    # graceful via NSSM SIGTERM → uvicorn shutdown
Get-Service "WEBSTUDIO Server"
```

View logs:

```
D:\WEBSTUDIO-IMS\logs\webstudio-api.log
D:\WEBSTUDIO-IMS\logs\webstudio-api-error.log
```

---

## Scheduler persistence

Scheduler timing is stored in `webstudio.scheduler_runtime_state` (migration **0035**). The API:

- Writes `next_run_at` after every scheduler cycle  
- Persists checkpoints every `WEBSTUDIO_SCHEDULER_PERSIST_SECONDS` (default 60)  
- On restart, sleeps until `next_run_at` instead of resetting intervals  

**Never restart scheduling from zero** after power-off — only elapsed time since last run is applied.

---

## Uninstall

```powershell
.\uninstall-webstudio-service.ps1 -InstallRoot "D:\WEBSTUDIO-IMS"
```

---

## Related scripts

| Script | Purpose |
|--------|---------|
| `ensure-postgresql.ps1` | Start PostgreSQL if stopped |
| `configure-service-recovery.ps1` | sc.exe failure actions |
| `start-business-day.ps1` | Morning startup sequence |
| `stop-business-day.ps1` | Evening graceful shutdown |
