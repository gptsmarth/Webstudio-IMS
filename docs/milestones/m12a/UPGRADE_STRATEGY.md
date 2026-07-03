---
Title: Upgrade Strategy
Version: 1.0.0
Status: Final — Awaiting Review
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12A
---

# Upgrade Strategy — Production Packaging Audit

**Purpose:** Define safe upgrade paths for server, database, desktop, and mobile once release artifacts exist. Aligns with [DEPLOYMENT_GUIDE.md](../../deployment/DEPLOYMENT_GUIDE.md) §14.

---

## Principles

1. **Backup before upgrade** — verified PostgreSQL dump mandatory  
2. **Server first, clients second** — API and schema ahead of or with clients  
3. **Migrations forward-only** — Alembic `upgrade head`; no downgrade scripts in repo  
4. **Maintenance window** — off-hours; notify users of Tally sync pause  
5. **Staging rehearsal** — same version on staging DB copy before production  

---

## Upgrade order (recommended)

```
1. Pre-upgrade backup + verify restore (monthly drill)
2. Stop / drain (optional: read-only banner)
3. Backend code + venv dependencies
4. alembic upgrade head
5. Restart API — smoke test /health and /api/v1/version
6. Desktop installers (Windows/macOS) — per workstation or IT push
7. Mobile APK/IPA — sideload or MDM; Flutter checks min_client_version
8. Post-upgrade smoke + Tally sync spot check
```

---

## Server (backend) upgrade

### Current procedure (source deploy)

| Step | Action |
|------|--------|
| 1 | `pg_dump` full database to timestamped file |
| 2 | Stop Windows service / uvicorn |
| 3 | Pull or copy new `apps/backend` tree |
| 4 | Activate venv; `pip install -e .` (or install from locked requirements) |
| 5 | `cd apps/backend && alembic upgrade head` |
| 6 | Start service; verify logs JSON on stdout |
| 7 | Run smoke: login, inventory list, Tally status |

### Future (M12+ packaged server)

Same logical steps; artifact may be zip + install script that preserves `.env` and runs Alembic automatically.

### Configuration migration

| Scenario | Action |
|----------|--------|
| New env vars in Settings | Merge from updated `.env.example`; restart |
| Settings stored in DB | Wizard/settings service picks up defaults on read |
| TLS cert renewal | Replace cert files; restart — no migration |

---

## Database upgrade

| Aspect | Detail |
|--------|--------|
| Tool | Alembic only |
| Head (audit date) | `0034_tally_incremental_sync` |
| Downtime | Brief — migrations run with API stopped |
| Large tables | Future: online migration ADR if needed; MVP migrations are DDL-light |

**Compatibility rule:** Server **must not** run old code against new schema or new code against old schema. Stop API during `alembic upgrade`.

**Tally note:** Migration 0034 adds sync history and fingerprint columns — no data backfill required for upgrade; incremental sync resumes from `last_successful_sync_at`.

---

## Desktop upgrade

### Target M12 flow

| Step | Action |
|------|--------|
| 1 | User runs new Setup.exe / mounts DMG |
| 2 | Installer replaces app; preserves `userData` (API URL, tokens if stored) |
| 3 | App reads server `/api/v1/version` on connect |
| 4 | Optional: show release notes modal |

**In-place vs clean install:** electron-builder NSIS should default to upgrade same install dir; document uninstall-only if profile corruption.

**Version check:** Desktop currently does **not** enforce `min_client_version` — recommend soft warning in M12+.

---

## Mobile upgrade

| Platform | Method |
|----------|--------|
| Android | Install new APK over existing (signing cert **must** match) |
| iOS | Replace via TestFlight / enterprise MDM / Xcode reinstall |

**Mandatory update:** Flutter compares `package_info` to server `min_client_version` — blocks app until upgrade if server requires newer client.

**API URL:** Preserved in `shared_preferences` — upgrade does not reset LAN URL.

---

## Coordinated release matrix

| Change type | Server | DB migration | Desktop | Mobile |
|-------------|--------|--------------|---------|--------|
| Patch bugfix | ✅ | Usually no | Optional | Optional |
| API additive | ✅ | Maybe | If UI uses feature | If UI uses feature |
| Schema change | ✅ | ✅ Required | If needed | If needed |
| Breaking API | ✅ | Maybe | ✅ Required | ✅ Required |

---

## Zero-downtime

**Not supported for MVP.** Single-server on-prem model expects brief API stop for migrations.

Future: read replicas + blue/green documented in ADR if product requires it.

---

## Upgrade testing checklist (staging)

- [ ] Restore production backup to staging DB  
- [ ] Apply new backend + `alembic upgrade head`  
- [ ] Run automated pytest subset + manual wizard/login  
- [ ] Install new desktop build against staging API  
- [ ] Install new APK:load APK against staging API  
- [ ] Tally incremental sync dry run (if enabled)  
- [ ] Document timing and rollback decision point  

---

## Automation targets (M12)

| Item | Owner |
|------|-------|
| Tag → build all artifacts | `release.yml` |
| Release notes template | docs/m12/releases/ |
| Alembic head in VERSION_MATRIX | bump script |
| Pre-upgrade backup reminder | Operator checklist in DEPLOY-001 |

---

## Related documents

- [ROLLBACK_STRATEGY.md](./ROLLBACK_STRATEGY.md)
- [DEPLOYMENT_GUIDE.md](../../deployment/DEPLOYMENT_GUIDE.md) §14
- [RELEASE_CHECKLIST.md](./RELEASE_CHECKLIST.md)
