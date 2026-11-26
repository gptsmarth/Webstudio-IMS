---
Title: Production Environment Configuration
Version: 1.0.0
Status: Final — Awaiting Review
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-11-22
Milestone: 12A
---

# Production Environment Configuration — Milestone 12A Audit

**Purpose:** Catalog environment variables, secrets, and production gates. Identifies gaps between runtime code and `config/env/.env.example`.

---

## Configuration layers

```
┌─────────────────────────────────────────────────────────┐
│  OS / host (paths, service wrapper, firewall)           │
├─────────────────────────────────────────────────────────┤
│  config/env/.env  (server secrets — not in git)         │
├─────────────────────────────────────────────────────────┤
│  Database settings table (wizard, Tally, schedulers)    │
├─────────────────────────────────────────────────────────┤
│  Desktop: userData, OS variables, and Vite defaults     │
├─────────────────────────────────────────────────────────┤
│  Flutter: shared_preferences (API URL, tokens)          │
└─────────────────────────────────────────────────────────┘
```

---

## Backend — core variables

**Source of truth:** `apps/backend/src/webstudio_backend/core/config.py`  
**Template:** `config/env/.env.example` (partial)

### Required for production

| Variable | Purpose | Production gate |
|----------|---------|-----------------|
| `APP_ENV` | `development` / `production` | Set `production` |
| `JWT_SECRET` | Token signing | Unique, cryptographically random secret of at least 32 bytes |
| `DATABASE_URL` | Async PostgreSQL URL | Required |
| `WEBSTUDIO_SECRET_ENCRYPTION_KEY` | Encrypt sensitive settings | Required for Tally credentials |

### Server binding & TLS

| Variable | Purpose | Default / notes |
|----------|---------|-----------------|
| `API_HOST` | Bind address | Restrict access with the server firewall |
| `API_PORT` | API listener port | `8000` |
| `TLS_CERT_PATH` | Full-chain server certificate | Set alongside `TLS_KEY_PATH` |
| `TLS_KEY_PATH` | Server private key | Store outside the repository and restrict it to the service account and administrators |
| `TLS_REQUIRED` | Require direct TLS configuration | Set `true` during secure commissioning after provisioning the certificate and key |

Give staff the HTTPS URL whose hostname matches the certificate. The client
devices must trust its issuer. Use that URL with the Windows
`finalize-server-setup.ps1 -ApiBaseUrl` health check and the client connection
test before enabling it for staff. Existing isolated HTTP installations can
continue during the certificate rollout.

### CORS & security

| Variable | Purpose |
|----------|---------|
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `RATE_LIMIT_ENABLED` | Enable per-client IP request limits |
| `RATE_LIMIT_PER_MINUTE` | General per-minute budget per client IP |
| `AUTH_RATE_LIMIT_PER_MINUTE` | Lower combined budget for login, refresh, and administrator recovery |

Keep the live `.env`, keys, backup files, Tally captures, and deployment snapshots
in restricted local directories. The GitHub release gate runs
`python3 scripts/release/check-private-files.py` before packaging. The committed
environment files are templates. If an earlier shared JWT secret was used on an
office server, rotate it during a maintenance window. Staff must sign in again.
The current server also encrypts saved integration keys and the Drive refresh
token using this secret. Plan to re-enter those keys and reconnect Drive after
rotation, if those integrations are in use.

### Logging

| Variable | Purpose |
|----------|---------|
| `LOG_LEVEL` | e.g. `INFO`, `DEBUG` |
| `LOG_JSON` | Force JSON logs (`true` in production recommended) |

JSON logging auto-enables when `APP_ENV=production` even if `LOG_JSON` unset.

### Schedulers (env overrides)

| Variable | Purpose |
|----------|---------|
| `WEBSTUDIO_TALLY_SCHEDULER_ENABLED` | Master Tally poll switch |
| `WEBSTUDIO_BACKUP_SCHEDULER_ENABLED` | Automated backup jobs |

**Gap:** These appear in code but not fully in `.env.example` — **M12: expand template**.

### Database pool

| Variable | Typical production |
|----------|-------------------|
| `DB_POOL_SIZE` | 5–20 by load |
| `DB_MAX_OVERFLOW` | 10 |

---

## Production validation gates (code)

| Gate | Trigger |
|------|---------|
| JWT secret length | `APP_ENV=production` → fail fast if weak |
| System initialized | API returns setup routes until wizard completes |
| TLS enforcement | `TLS_REQUIRED=true` requires both TLS paths at startup |

---

## Desktop configuration

### Build-time (Vite)

| Variable | Current use |
|----------|-------------|
| `VITE_API_BASE_URL` | Optional default API URL in dev |
| `VITE_*` | Minimal — most config runtime |

### Runtime

| Storage | Contents |
|---------|----------|
| Electron `userData` | Client log file, window state |
| localStorage / secure storage | Session tokens, API base URL |
| `buildVersion` in main process | Hardcoded — replace with build injection |

### Production gates needed (M12)

| Gate | Purpose |
|------|---------|
| `WEBSTUDIO_DISABLE_DEMO_MODE=true` or production build flag | Block Preview/demo (11Y-H01) |
| Optional CSP meta / headers | Renderer hardening (11Y-H08) |

---

## Google Drive OAuth for Windows

Use the **same Google OAuth Desktop app client ID and client secret** in both
locations below. The server uses the pair to refresh access and upload backups.
WEBSTUDIO Desktop uses it on the administrator's Windows computer for the
one-time **Connect Google Drive** authorization in the browser. If the
administrator runs Desktop on the server itself, complete both steps on that PC.
If Desktop runs on a separate PC, complete the server step on the server and
the Desktop step on that PC. [Google Cloud project and OAuth client setup](../../architecture/future/cloud-backup-sync.md#7-google-cloud-setup)

### A. Configure the IMS server

On the Windows server, the backend runtime file is
`D:\WEBSTUDIO-IMS\apps\backend\.env`. It must contain both entries below,
with the placeholders replaced by the credentials from the same OAuth client.

```ini
GOOGLE_DRIVE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_DRIVE_CLIENT_SECRET=your_google_oauth_client_secret
```

For a Server Setup installation, edit the source file
`D:\WEBSTUDIO-IMS\config\env\.env` as an administrator. Add or update each
entry once. Set `WEBSTUDIO_CLOUD_BACKUP_SYNC_SCHEDULER=1` if you want automatic
uploads. Then run this in **Administrator Windows PowerShell** to copy the
settings into `apps\backend\.env` and `apps\backend\config\env\.env` and
restart **WEBSTUDIO Server**. Editing the runtime copy alone can be overwritten
by a later sync or upgrade.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'D:\WEBSTUDIO-IMS\infra\windows\sync-backend-env.ps1' -InstallRoot 'D:\WEBSTUDIO-IMS' -RestartService
```

For a manually managed backend where `apps\backend\.env` is the active source,
edit that file directly, then restart the service in **Administrator Windows
PowerShell**. Use the actual installation path if it differs.

```powershell
Restart-Service -Name 'WEBSTUDIO Server' -ErrorAction Stop
```

### B. Configure the Windows PC running WEBSTUDIO Desktop

Open **Windows PowerShell as Administrator** on the PC where the administrator
will click **Connect Google Drive**. Replace both placeholders with the same
pair used on the server. The commands write persistent Windows **Machine**
environment variables, shown as **System variables** in Windows. Keep these
credentials on the trusted administrator's PC. Never include the secret in
screenshots, logs, support messages, or Git. Use a private session without
transcription or saved command history when entering real values, or enter
them under **Advanced system settings → Environment Variables → System
variables**. [Microsoft guide to Windows environment variables](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_environment_variables)

```powershell
[Environment]::SetEnvironmentVariable("GOOGLE_DRIVE_CLIENT_ID", "YOUR_CLIENT_ID", "Machine")
[Environment]::SetEnvironmentVariable("GOOGLE_DRIVE_CLIENT_SECRET", "YOUR_CLIENT_SECRET", "Machine")
```

### Verify the Windows variables

On the Desktop PC, run the following in PowerShell. Both entries should say
`PRESENT`. The check shows whether a value is set and keeps the values private.

```powershell
foreach ($Key in @("GOOGLE_DRIVE_CLIENT_ID", "GOOGLE_DRIVE_CLIENT_SECRET")) {
    $Value = [Environment]::GetEnvironmentVariable($Key, "Machine")
    Write-Output "$Key : $(if ([string]::IsNullOrWhiteSpace($Value)) {'MISSING'} else {'PRESENT'})"
}
```

### Restart Desktop and connect Google Drive

1. Completely exit **WEBSTUDIO Desktop**.
2. Open **Task Manager** and make sure all **WEBSTUDIO Desktop** processes have closed.
3. Launch Desktop again from the **Start menu** so it inherits the new variables.
4. Sign in as Main Admin and open **Settings → Backup → Backup policy**.
   Select **Google Drive** under **Storage backend** and save the policy.
5. In **Google Drive**, select **Connect Google Drive**. Sign in to the account
   that should receive backups and complete the browser authorization.
6. Confirm **Connected account** shows the intended account. Run a manual backup
   and after the next cloud sync cycle check **Last sync**, **Sync status**, and
   the **WEBSTUDIO Backups** folder in Drive.

A **WEBSTUDIO Server** service restart refreshes the backend configuration.
Desktop reads its own Windows process environment at startup and needs its
own restart, even when both programs run on the same PC.

### Troubleshoot Google Drive OAuth

> Google Drive is not configured on this installation. Set GOOGLE_DRIVE_CLIENT_ID and GOOGLE_DRIVE_CLIENT_SECRET and restart the app.

If the server already loads both credentials and Desktop shows this message,
check the [Machine variables](#verify-the-windows-variables) on the PC where
Desktop is running. Set any missing value, close all Desktop processes, and
relaunch from the Start menu. If both values are present and the message
persists, sign out of Windows and back in, then reopen Desktop.

If browser authorization completes but connecting or uploading fails, confirm
privately that the server and Desktop use the **same** OAuth client pair and
that the server restarted after the edit. If authorization expires after about
a week, check the OAuth app's publishing status. An External app in **Testing**
issues seven-day refresh tokens for Drive access. Publish the app and reconnect
through Desktop for a fresh authorization. [Google's refresh-token rules](https://developers.google.com/identity/protocols/oauth2#expiration)

---

## Flutter configuration

| Mechanism | Contents |
|-----------|----------|
| `AppConfig` / preferences | Discovered or manual API URL |
| `--dart-define` | **Not used today** — optional for fixed-URL enterprise builds |
| `AndroidManifest` / iOS plist | Permissions, bundle ID |

**Production:** No embedded production API URL by design (LAN discovery model).

---

## PostgreSQL (compose / production)

| Variable | Dev compose |
|----------|-------------|
| `POSTGRES_USER` | `webstudio` |
| `POSTGRES_PASSWORD` | From `.env` |
| `POSTGRES_DB` | `webstudio` |

Production: dedicated DB user with least privilege; not superuser.

---

## Secrets management

| Secret | Storage | Never |
|--------|---------|-------|
| JWT_SECRET | Server `.env` | Commit |
| DB password | Server `.env` | Commit |
| Encryption key | Server `.env` | Commit |
| Android keystore | CI secret / HSM | Commit |
| Apple certs | CI secret / keychain | Commit |
| Tally credentials | DB encrypted fields | Plaintext in logs |
| Google Drive OAuth client secret | Server's restricted `.env` and administrator's Windows Machine environment | Commit, log, or share in screenshots |

---

## Environment matrix

| Environment | APP_ENV | DATABASE | TLS | Demo mode |
|-------------|---------|----------|-----|-----------|
| Local dev | development | Docker compose | Off | Allowed |
| Staging | production | Staging PG | Optional | Disabled |
| Customer prod | production | Customer PG | Recommended | **Disabled** |

---

## `.env.example` gap list (M12 fix)

Document in template (audit findings):

- [ ] Scheduler env vars (`WEBSTUDIO_*_SCHEDULER_*`)
- [ ] SSL variable names aligned with `config.py`
- [ ] `WEBSTUDIO_SECRET_ENCRYPTION_KEY` generation hint
- [ ] CORS / trusted hosts examples for LAN
- [ ] Link to DEPLOY-001 first-time wizard

---

## First-time production bootstrap

1. Install PostgreSQL + Python  
2. Copy `.env.example` → `.env`; set secrets  
3. `alembic upgrade head`  
4. Start API  
5. Complete setup wizard (creates admin, brand, location)  
6. Configure Tally in settings UI (optional)  
7. Deploy desktop/mobile; point to server URL  

---

## Related documents

- [LOGGING_STRATEGY.md](./LOGGING_STRATEGY.md)
- [RUNTIME_DEPENDENCIES.md](./RUNTIME_DEPENDENCIES.md)
- [config/env/.env.example](../../../config/env/.env.example)
- [DEPLOYMENT_GUIDE.md](../../deployment/DEPLOYMENT_GUIDE.md)
- [Google Drive Cloud Backup Sync](../../architecture/future/cloud-backup-sync.md#7-google-cloud-setup)
