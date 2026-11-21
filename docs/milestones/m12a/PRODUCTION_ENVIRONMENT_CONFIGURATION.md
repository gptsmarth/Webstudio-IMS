---
Title: Production Environment Configuration
Version: 1.0.0
Status: Final — Awaiting Review
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
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
│  Desktop: userData + build-time VITE_* (minimal today)  │
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
