---
Title: Deployment Guide — Milestone 12B Windows Server
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12B
Related Documents:
  - docs/deployment/DEPLOYMENT_GUIDE.md
  - docs/milestones/m12b/WINDOWS_SERVICE_GUIDE.md
---

# Deployment Guide — Business-Hours Windows Server (M12B)

Extends [DEPLOY-001](../../deployment/DEPLOYMENT_GUIDE.md) for **dedicated Windows 11 Pro** servers that power **off every evening**.

---

## Architecture

```
Windows 11 Pro Server PC
├── PostgreSQL 16 (Windows Service)
├── WEBSTUDIO Server Service (NSSM → Python uvicorn)
│   ├── Startup orchestration
│   ├── Scheduler runtime state (PostgreSQL)
│   └── Graceful shutdown
└── D:\WEBSTUDIO-IMS\  (data root)

Clients (LAN)
├── WEBSTUDIO Desktop (Electron) — auto-reconnect every 15 s
└── WEBSTUDIO IMS Mobile (Flutter) — auto-reconnect every 15 s
```

---

## Directory layout

Create on the server:

| Path | Purpose |
|------|---------|
| `D:\WEBSTUDIO-IMS\apps\backend` | API source / release copy |
| `D:\WEBSTUDIO-IMS\venv` | Python virtual environment |
| `D:\WEBSTUDIO-IMS\config\env\.env` | Production secrets |
| `D:\WEBSTUDIO-IMS\logs\` | Service stdout/stderr (NSSM) |
| `D:\WEBSTUDIO-IMS\backups\` | PostgreSQL dumps |
| `D:\WEBSTUDIO-IMS\certs\` | TLS certificate |
| `D:\WEBSTUDIO-IMS\tools\nssm\` | NSSM binary |

---

## Deployment steps

### 1. Install PostgreSQL 16

- Localhost only (`5432`)  
- Create `webstudio` database and application user  
- Note Windows service name (e.g. `postgresql-x64-16`)

### 2. Deploy backend

```powershell
cd D:\WEBSTUDIO-IMS\apps\backend
..\..\venv\Scripts\pip install -e .
..\..\venv\Scripts\python -m alembic upgrade head
```

Ensure migration **0035_scheduler_runtime_state** is applied.

### 3. Configure environment

Copy `config/env/.env.example` → `D:\WEBSTUDIO-IMS\config\env\.env`:

- `APP_ENV=production`  
- `JWT_SECRET` ≥ 32 bytes  
- `DATABASE_URL`  
- `API_HOST=0.0.0.0`  
- `API_PORT=8443`  
- `TLS_CERT_PATH` / `TLS_KEY_PATH`  
- `WEBSTUDIO_DATA_ROOT=D:\WEBSTUDIO-IMS`  
- Scheduler flags (`WEBSTUDIO_*_SCHEDULER=1`)

### 4. Install WEBSTUDIO Server Service

```powershell
.\infra\windows\install-webstudio-service.ps1
```

See [WINDOWS_SERVICE_GUIDE.md](./WINDOWS_SERVICE_GUIDE.md).

### 5. First-time setup

1. Open Desktop client → connect to server HTTPS URL  
2. Complete setup wizard  
3. Configure Tally and backup schedule in Admin settings  

### 6. Install clients

- Desktop: Setup.exe on staff PCs (saved API URL persists across server restarts)  
- Mobile: sideload APK; QR/manual URL unchanged  

---

## Health verification

```powershell
Invoke-RestMethod https://192.168.1.100:8443/health/ready -SkipCertificateCheck
```

Expected: `status: ready`, `database: ok`, `disk_space: ok`, `startup: ok`.

---

## Upgrade procedure

1. Evening: `stop-business-day.ps1`  
2. Backup database  
3. Deploy new backend code + `alembic upgrade head`  
4. Morning: `start-business-day.ps1` or reboot  
5. Verify `/health/ready` and scheduler state restored  

---

## Client reconnection

No user action required after server power-on:

| Client | Behaviour |
|--------|-----------|
| Desktop | Polls `/health/live` every 15 s in workspace; retries session on recovery |
| Flutter | `ServerReconnectLifecycleObserver` polls health every 15 s |

Saved API URL and refresh tokens remain on the client.

---

## Related documents

- [BUSINESS_HOURS_DEPLOYMENT_GUIDE.md](./BUSINESS_HOURS_DEPLOYMENT_GUIDE.md)  
- [RECOVERY_GUIDE.md](./RECOVERY_GUIDE.md)
