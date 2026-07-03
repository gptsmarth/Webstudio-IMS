---
Title: Server Guide — WEBSTUDIO IMS
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12H
---

# Server Guide

Operate the **WEBSTUDIO Server** on a dedicated Windows 11 Pro PC.

---

## 1. Server role

The server PC runs:

| Component | Purpose |
|-----------|---------|
| PostgreSQL 16 | Database (`webstudio` schema) |
| WEBSTUDIO API | FastAPI on port 8000 |
| Schedulers | Tally sync, backup, audit retention, notifications |
| mDNS | Optional LAN advertisement |

Clients connect over LAN only — no cloud dependency for daily operations.

---

## 2. Directory layout

Default root: `D:\WEBSTUDIO-IMS`

```
D:\WEBSTUDIO-IMS\
├── apps\backend\          # Python application
├── config\env\.env        # Secrets (not in git)
├── logs\
│   ├── webstudio-api.log
│   └── crash\webstudio-crash.log
├── backups\               # Local backup archives
├── exports\               # Excel exports
├── assets\product-images\
└── venv\                  # Python virtual environment
```

---

## 3. Windows service

| Property | Value |
|----------|-------|
| Name | `WEBSTUDIO Server` |
| Start | Automatic (Delayed Start) |
| Manager | NSSM |
| Logs | `logs\webstudio-api.log` (stdout redirect) |

```powershell
# Status
sc query "WEBSTUDIO Server"

# Start / stop
Start-Service "WEBSTUDIO Server"
Stop-Service "WEBSTUDIO Server"   # graceful shutdown orchestrator runs
```

Full detail: [M12B Windows Service Guide](../m12b/WINDOWS_SERVICE_GUIDE.md)

---

## 4. Environment variables

Copy from `config/env/.env.production`. Key variables:

| Variable | Production |
|----------|------------|
| `APP_ENV` | `production` |
| `WEBSTUDIO_DATA_ROOT` | `D:\WEBSTUDIO-IMS` |
| `WEBSTUDIO_TALLY_SCHEDULER` | `1` |
| `WEBSTUDIO_LOG_DIR` | `D:\WEBSTUDIO-IMS\logs` |
| `JWT_SECRET` | ≥32 bytes, installer-generated |

---

## 5. Database

- Engine: PostgreSQL 16
- Service: `postgresql-x64-16` (typical)
- Migrations: Alembic — head in `version-manifest.json`

```powershell
cd D:\WEBSTUDIO-IMS\apps\backend
.\venv\Scripts\alembic.exe upgrade head
```

---

## 6. Schedulers

| Scheduler | Env flag | Default interval |
|-----------|----------|------------------|
| Tally sync | `WEBSTUDIO_TALLY_SCHEDULER=1` | 300s (settings) |
| Backup | `WEBSTUDIO_BACKUP_SCHEDULER=1` | 900s |
| Tally probe | `WEBSTUDIO_TALLY_CONNECTIVITY_PROBE=1` | 120s |

State persists in `webstudio.scheduler_runtime_state` across restarts.

---

## 7. Health checks

```powershell
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

`/health/ready` includes database and migration status.

---

## 8. Business hours operation

| Morning | Server PC power on → PostgreSQL → WEBSTUDIO service |
| Evening | Graceful stop → optional PostgreSQL stop |

Scripts: `infra/windows/start-business-day.ps1`, `stop-business-day.ps1`

---

## 9. Logs

| Log | Location |
|-----|----------|
| API | `WEBSTUDIO_LOG_DIR/webstudio-api.log` |
| Crash | `WEBSTUDIO_CRASH_LOG_DIR/webstudio-crash.log` |
| NSSM stdout | `logs/webstudio-api.log` |

See `config/logging/production-logging.md`

---

## 10. Upgrade server

1. Backup database
2. Stop service
3. Replace application files or run new installer
4. `alembic upgrade head`
5. Start service
6. Verify `/health/ready`

[M12G Release Engineering](../m12g/RELEASE_ENGINEERING_REPORT.md)
