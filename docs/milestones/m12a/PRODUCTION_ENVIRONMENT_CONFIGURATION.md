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
| `JWT_SECRET` | Token signing | **≥32 bytes** when production |
| `DATABASE_URL` | Async PostgreSQL URL | Required |
| `WEBSTUDIO_SECRET_ENCRYPTION_KEY` | Encrypt sensitive settings | Required for Tally credentials |

### Server binding & TLS

| Variable | Purpose | Default / notes |
|----------|---------|-----------------|
| `HOST` | Bind address | `0.0.0.0` for LAN server |
| `PORT` | HTTP port | `8000` |
| `WEBSTUDIO_SSL_ENABLED` | Enable HTTPS | `false` dev |
| `WEBSTUDIO_SSL_CERTFILE` | TLS cert path | When SSL enabled |
| `WEBSTUDIO_SSL_KEYFILE` | TLS key path | When SSL enabled |

**Audit note:** DEPLOYMENT_GUIDE may use alternate names — reconcile in M12 docs pass.

### CORS & security

| Variable | Purpose |
|----------|---------|
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `WEBSTUDIO_TRUSTED_HOSTS` | Host header validation |

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
| TLS optional | Operator choice — LAN HTTP acceptable per DEPLOY-001 with network isolation |

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
