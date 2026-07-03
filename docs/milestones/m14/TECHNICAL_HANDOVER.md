---
Title: Technical Handover
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14J
---

# Technical Handover (M14J)

Engineering reference for WEBSTUDIO IMS v1.0.0 production deployment.

---

## Architecture

| Layer | Technology |
|-------|------------|
| API | FastAPI (Python), Uvicorn |
| Database | PostgreSQL 16, schema `webstudio` |
| Desktop | Electron + React + TypeScript |
| Mobile | Flutter (Android/iOS) |
| Server OS | Windows 11 Pro dedicated PC |

**Authority:** [docs/SYSTEM_ARCHITECTURE.md](../../SYSTEM_ARCHITECTURE.md)

---

## Install topology

```
Dedicated Server (Windows 11 Pro)
├── WEBSTUDIO Server (Windows Service, port 8000)
├── PostgreSQL 16 (localhost:5432)
└── Backups / logs / release catalog

LAN Clients
├── Desktop (Windows EXE, macOS DMG)
└── Mobile (Android APK, iOS IPA)

Billing PC
└── Tally ERP 9 XML :9000
```

---

## Version identity

| Source | Value |
|--------|-------|
| `VERSION.json` | 1.0.0 / stable / PRODUCTION READY |
| Alembic head | `0042_deployment_monitoring` |
| API | `GET /api/v1/version` |

---

## Key APIs

| Domain | Base path |
|--------|-----------|
| Health | `/health/live`, `/health/ready` |
| Auth | `/api/v1/auth/*` |
| Inventory | `/api/v1/inventory` |
| Tally | `/api/v1/integrations/tally` |
| Backups | `/api/v1/settings/backups` |
| Deployment Center | `/api/v1/deployment/center` |
| Client updates | `/api/v1/client-updates` |
| Handover validation | `/api/v1/deployment/production-handover` |

---

## Release pipeline

1. GitHub Release (source bundles)
2. `GitHubReleaseSyncService` → server catalog
3. Deployment Center → administrator approve → deploy
4. Clients poll `/client-updates/check` — **never GitHub**

---

## Schedulers

| Key | Default interval |
|-----|------------------|
| `tally_sync` | 300s |
| `backup` | 900s |
| `github_release_sync` | 900s |
| `notification_delivery` | 300s |
| `tally_connectivity_probe` | 120s |

State: `webstudio.scheduler_runtime_state`

---

## Security summary

- JWT HS256, Argon2id passwords, RBAC + custom roles
- Integration keys Fernet-encrypted
- PostgreSQL localhost-only
- LAN firewall TCP 8000 inbound

See [SECURITY_CERTIFICATION.md](SECURITY_CERTIFICATION.md).

---

## Repository handover

| Path | Purpose |
|------|---------|
| `apps/backend/` | API source |
| `apps/desktop/` | Desktop client |
| `apps/mobile/` | Flutter client |
| `database/migrations/` | Alembic |
| `infra/windows/` | Server scripts |
| `docs/milestones/m14/` | Production pack |
| `release/v1.0.0/` | Release bundle |

---

## Support contacts

WEBSTUDIO IMS Team — engineering escalation for P1/P2 production incidents.
