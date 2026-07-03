---
Title: WEBSTUDIO IMS — Production Installation Manual
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14A
Related Documents:
  - docs/milestones/m14/M14_GLOBAL_RULES.md
  - docs/milestones/m12c/INSTALLER_GUIDE.md
  - docs/milestones/m12b/WINDOWS_SERVICE_GUIDE.md
  - docs/milestones/m12h/SERVER_GUIDE.md
---

# WEBSTUDIO IMS — Production Installation Manual

Authoritative **step-by-step** installation sequence for a dedicated **Windows 11 Pro** server PC (enterprise “Windows server” role in WEBSTUDIO IMS). Uses packaged artifacts and scripts from M12/M13 — **no custom code changes** at install time.

**Install root (default):** `D:\WEBSTUDIO-IMS`  
**Service name:** `WEBSTUDIO Server`  
**API port:** `8000` (LAN)

---

## Before you begin

| Item | Requirement |
|------|-------------|
| Hardware | Dedicated PC, UPS recommended, ≥20% free disk |
| OS | Windows 11 Pro (patched, NTP enabled) |
| Network | Static IP or DHCP reservation; staff LAN access |
| Artifacts | `WEBSTUDIO Server Setup.exe` from stable release bundle |
| Operator | Local Administrator on server PC |
| Main Admin | Named person for Setup Wizard (step 13–14) |

Verify release checksums from `checksums.sha256` in the release bundle before copying installers to the server.

---

## Installation sequence

### Step 1 — Windows server installation

Prepare the dedicated server PC.

1. Install **Windows 11 Pro** and apply updates.
2. Set **computer name** (e.g. `WEBSTUDIO-SERVER`).
3. Configure **static IPv4** or DHCP reservation; document IP and hostname.
4. Enable **Windows Firewall** — allow inbound TCP **8000** from office subnet only (configure after API is listening).
5. Optional: register hostname in internal DNS (`webstudio-server.local`).
6. Create install root if not using default: `D:\WEBSTUDIO-IMS`.

**Validation**

- [ ] `winver` shows Windows 11 Pro
- [ ] Time zone and NTP correct
- [ ] Administrator account available

**Reference:** [m12h/NETWORKING_GUIDE.md](../m12h/NETWORKING_GUIDE.md)

---

### Step 2 — PostgreSQL installation

PostgreSQL **16.x** is required. It may be installed by the server setup installer or pre-installed.

#### Option A — Bundled with WEBSTUDIO Server Setup

Place `postgresql-installer.exe` in installer payload (see [m12c/INSTALLER_GUIDE.md](../m12c/INSTALLER_GUIDE.md)). Setup detects service `postgresql-x64-16` and runs silent install if missing.

#### Option B — Manual install

1. Install PostgreSQL 16 for Windows.
2. Set service name **`postgresql-x64-16`** (or note actual name for scripts).
3. Create database and application user per your security policy.
4. Ensure service **Start type: Automatic**.

**Validation**

```powershell
Get-Service postgresql-x64-16
# Status should be Running
```

```powershell
& "D:\WEBSTUDIO-IMS\infra\windows\ensure-postgresql.ps1" -PostgresServiceName "postgresql-x64-16"
```

---

### Step 3 — WEBSTUDIO Server installation

1. Copy **`WEBSTUDIO Server Setup.exe`** to the server.
2. Run **as Administrator**.
3. Confirm install path `D:\WEBSTUDIO-IMS` (or chosen root).
4. Allow installer to copy:
   - `apps\backend`
   - `database\` (migrations)
   - `config\env\` templates
   - Windows infra scripts

Post-install script (`server-install-post.ps1`) runs automatically:

- Creates `logs`, `backups`, `certs`, `exports`, `config\env`
- Ensures PostgreSQL
- Creates Python venv dependencies (`pip install -e .`)
- Runs Alembic (step 6)
- Registers Windows Service (step 4)

**Validation**

- [ ] `D:\WEBSTUDIO-IMS\apps\backend` exists
- [ ] `D:\WEBSTUDIO-IMS\venv\Scripts\python.exe` exists
- [ ] `D:\WEBSTUDIO-IMS\config\env\.env` exists (generated if absent)

---

### Step 4 — Windows Service registration

Normally performed by installer via `install-webstudio-service.ps1`.

| Setting | Value |
|---------|--------|
| Service name | `WEBSTUDIO Server` |
| Startup | Automatic (Delayed Start) |
| Wrapper | NSSM |
| Executable | `{InstallRoot}\venv\Scripts\python.exe` |
| Arguments | `-m webstudio_backend.main` |
| Working directory | `{InstallRoot}\apps\backend` |

**Manual re-install (if needed)**

```powershell
cd D:\WEBSTUDIO-IMS\infra\windows
.\install-webstudio-service.ps1 -InstallRoot "D:\WEBSTUDIO-IMS" -PostgresServiceName "postgresql-x64-16"
```

**Validation**

```powershell
Get-Service "WEBSTUDIO Server"
sc query "WEBSTUDIO Server"
```

Expected: `STATE: RUNNING` (or `START_PENDING` briefly after install).

**Reference:** [m12b/WINDOWS_SERVICE_GUIDE.md](../m12b/WINDOWS_SERVICE_GUIDE.md)

---

### Step 5 — Environment configuration

Edit **`D:\WEBSTUDIO-IMS\config\env\.env`** (installer seeds from `.env.production.template` and generates `JWT_SECRET`).

#### Required production values

| Variable | Example / rule |
|----------|----------------|
| `APP_ENV` | `production` |
| `JWT_SECRET` | ≥32 bytes random (installer-generated) |
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@localhost:5432/webstudio` |
| `WEBSTUDIO_DATA_ROOT` | `D:\WEBSTUDIO-IMS` |
| `API_HOST` | `0.0.0.0` |
| `API_PORT` | `8000` |
| `LOG_LEVEL` | `INFO` |
| `LOG_JSON` | `true` |

#### Scheduler switches (NSSM also sets these; keep consistent in `.env`)

| Variable | Production |
|----------|------------|
| `WEBSTUDIO_TALLY_SCHEDULER` | `1` |
| `WEBSTUDIO_BACKUP_SCHEDULER` | `1` |
| `WEBSTUDIO_NOTIFICATION_SCHEDULER` | `1` |
| `WEBSTUDIO_MAINTENANCE_SCHEDULER` | `1` |
| `WEBSTUDIO_AUDIT_RETENTION_SCHEDULER` | `1` |
| `WEBSTUDIO_TALLY_CONNECTIVITY_PROBE` | `1` |

Restart service after `.env` changes:

```powershell
Restart-Service "WEBSTUDIO Server"
```

**Validation**

- [ ] No plaintext default passwords in production `.env`
- [ ] `JWT_SECRET` length ≥32 characters

**Reference:** [m12a/PRODUCTION_ENVIRONMENT_CONFIGURATION.md](../m12a/PRODUCTION_ENVIRONMENT_CONFIGURATION.md)

---

### Step 6 — Database initialization

Performed automatically during install. Re-run after upgrades only.

```powershell
cd D:\WEBSTUDIO-IMS\apps\backend
D:\WEBSTUDIO-IMS\venv\Scripts\python.exe -m alembic upgrade head
```

**Validation**

```sql
SELECT version_num FROM webstudio.alembic_version;
```

Expected head at release time: **`0042_deployment_monitoring`** (or current `VERSION.json` / release manifest `database.alembic_head`).

```powershell
# From any LAN machine with curl:
curl http://<server-ip>:8000/health/ready
```

Expected: database check `ok` in response payload.

---

### Step 7 — Scheduler initialization

On first service start, **startup orchestration** runs:

1. Verifies PostgreSQL, storage, configuration
2. Calls `SchedulerRuntimeService.restore_all()` — loads `webstudio.scheduler_runtime_state`
3. Syncs Tally interval from settings when Tally is enabled
4. Background tasks start per env flags (steps 8–10)

**Validation**

```powershell
curl http://<server-ip>:8000/health/ready
```

Inspect `scheduler_state` in ready payload (when exposed) or query:

```sql
SELECT scheduler_key, last_run_at, next_run_at, last_run_status
FROM webstudio.scheduler_runtime_state
ORDER BY scheduler_key;
```

Expected keys include: `tally_sync`, `backup`, `notification_delivery`, `audit_retention`, `maintenance`, `tally_connectivity_probe`, `github_release_sync`.

**Reference:** `apps/backend/src/webstudio_backend/services/startup_orchestrator.py`

---

### Step 8 — Backup scheduler

Enabled when `WEBSTUDIO_BACKUP_SCHEDULER=1` (default in production service).

Configure schedule in **Settings → Backup** after Setup Wizard (default may be `manual` until admin sets schedule).

**Validation**

- [ ] Service env includes `WEBSTUDIO_BACKUP_SCHEDULER=1`
- [ ] `scheduler_runtime_state` row for `backup` exists after first API start
- [ ] After wizard: backup path under `D:\WEBSTUDIO-IMS\backups\`

**Reference:** [m12h/BACKUP_GUIDE.md](../m12h/BACKUP_GUIDE.md)

---

### Step 9 — Notification scheduler

Enabled when `WEBSTUDIO_NOTIFICATION_SCHEDULER=1`.

Delivers in-app notifications (backup alerts, security alerts, etc.) per system settings.

**Validation**

- [ ] `WEBSTUDIO_NOTIFICATION_SCHEDULER=1` in service environment
- [ ] `notification_delivery` row in `scheduler_runtime_state`
- [ ] No errors in `D:\WEBSTUDIO-IMS\logs\webstudio-api.log` referencing notification scheduler

---

### Step 10 — Tally scheduler

Enabled when `WEBSTUDIO_TALLY_SCHEDULER=1`. **Tally integration** must be configured in Settings after wizard (host, company, XML port 9000 on billing PC).

Until Tally is configured, scheduler runs but sync remains disabled in settings.

**Validation**

- [ ] `WEBSTUDIO_TALLY_SCHEDULER=1`
- [ ] `tally_sync` scheduler row present
- [ ] After Tally settings: **Settings → Tally** shows enabled host/company
- [ ] Tally Sync Health shows expected state (post-commissioning)

**Reference:** [m12h/TALLY_GUIDE.md](../m12h/TALLY_GUIDE.md), [m12e/TALLY_DEPLOYMENT_GUIDE.md](../m12e/TALLY_DEPLOYMENT_GUIDE.md)

---

### Step 11 — AI provider configuration

Optional but recommended for Add Laptop enrichment.

**Environment (server `.env`)** — at least one:

| Variable | Provider |
|----------|----------|
| `GEMINI_API_KEY` | Google Gemini |
| `GROQ_API_KEY` | Groq |
| `OPENROUTER_API_KEY` | OpenRouter |

**Settings (after login)** — Settings → Integrations:

1. Enable **AI enrichment**
2. Select primary provider and fallback chain
3. Run **Test AI**

Startup check `ai_configuration` returns `warning` if enrichment is enabled without keys — not a hard failure.

**Reference:** [m12h/AI_GUIDE.md](../m12h/AI_GUIDE.md)

---

### Step 12 — API key configuration

**Integration API keys** (for external systems) are managed in **Settings → Administration → Integration keys** by Main Admin after setup.

1. Log in as Main Admin
2. Create keys per service type (read-only mobile list if `integration_keys:manage` granted)
3. Store key material offline; keys are shown once at creation

Keys are encrypted at rest (Fernet). Not required for first boot — configure before enabling third-party integrations.

**API:** `GET/POST /api/v1/admin/integration-keys` (admin permission required)

---

### Step 13 — First administrator login

Until Setup Wizard completes, **only setup routes** are available; standard login is blocked for uninitialized systems.

1. Install **WEBSTUDIO Desktop** on admin PC ([m12c/INSTALLER_GUIDE.md](../m12c/INSTALLER_GUIDE.md)).
2. Launch desktop app; connect via mDNS or manual URL: `http://<server-ip>:8000`.
3. App detects `system_initialized: false` and shows **Setup Wizard** (not login).

**Validation**

```http
GET /api/v1/setup/status
```

Expected before wizard:

```json
{ "system_initialized": false, ... }
```

---

### Step 14 — Setup Wizard completion

Complete all three wizard steps on desktop:

| Step | Action |
|------|--------|
| 1 — Organization | Company name |
| 2 — Administrator | Main Admin name, username, password |
| 3 — Recovery Key | Display key → **offline storage** → confirm acknowledgment |

API flow:

1. `POST /api/v1/setup/initialize` — creates Main Admin, company, recovery key
2. `POST /api/v1/setup/confirm-recovery-key` — sets `system_initialized=true`

**Validation**

- [ ] `GET /api/v1/setup/status` → `system_initialized: true`
- [ ] Login with Main Admin credentials succeeds
- [ ] Recovery key stored in secure offline location (safe / password manager / sealed envelope)
- [ ] Audit log contains `system_initialize` event

**Reference:** `apps/desktop/src/pages/SetupWizardPage.tsx`, `setup_service.py`

---

## Post-installation

| Task | Guide |
|------|-------|
| Commissioning & smoke tests | [PRODUCTION_COMMISSIONING_GUIDE.md](PRODUCTION_COMMISSIONING_GUIDE.md) |
| First boot checklist | [FIRST_STARTUP_CHECKLIST.md](FIRST_STARTUP_CHECKLIST.md) |
| Business-hours power cycle | [m12b/BUSINESS_HOURS_DEPLOYMENT_GUIDE.md](../m12b/BUSINESS_HOURS_DEPLOYMENT_GUIDE.md) |
| Desktop / mobile clients | [m12h/DESKTOP_GUIDE.md](../m12h/DESKTOP_GUIDE.md), [m12h/ANDROID_GUIDE.md](../m12h/ANDROID_GUIDE.md) |

---

## Troubleshooting

| Symptom | Action |
|---------|--------|
| Service won't start | Check `logs\webstudio-api-error.log`, PostgreSQL running, `DATABASE_URL` |
| `/health/ready` fails DB | Re-run Alembic; verify PostgreSQL credentials |
| Wizard won't appear | Confirm `system_initialized` is false; check API URL in desktop |
| Schedulers not running | Verify env flags; restart service; check `scheduler_runtime_state` |
| JWT errors | Ensure `JWT_SECRET` ≥32 bytes and service restarted |

**Reference:** [m12h/TROUBLESHOOTING_GUIDE.md](../m12h/TROUBLESHOOTING_GUIDE.md)
