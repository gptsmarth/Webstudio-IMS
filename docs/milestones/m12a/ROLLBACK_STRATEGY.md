---
Title: Rollback Strategy
Version: 1.0.0
Status: Final — Awaiting Review
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12A
---

# Rollback Strategy — Production Packaging Audit

**Purpose:** Recovery procedures when an upgrade fails or a release artifact is defective. Complements [UPGRADE_STRATEGY.md](./UPGRADE_STRATEGY.md) and DEPLOY-001 §13.

---

## Principles

1. **Database rollback = restore from backup** — Alembic has no tested downgrade path  
2. **Keep N-1 artifacts** — previous Setup.exe, DMG, APK, IPA alongside new release  
3. **Time-bound decision** — if migration succeeded but app faulty, restore DB **only if** post-migration writes must be discarded  
4. **Document every rollback** — incident log with versions, backup filename, operator  

---

## Failure scenarios

| Scenario | Rollback approach |
|----------|-------------------|
| Migration fails mid-run | Fix forward or restore pre-upgrade DB; do not start new code |
| Migration succeeds, API won't start | Restore previous backend code; DB may still be new schema — **restore DB if incompatible** |
| API runs but data corruption | Stop API; restore verified backup; replay exports if partial |
| Desktop installer bad | Reinstall previous Setup.exe / DMG |
| Mobile APK bad | Reinstall previous APK (same signing key) |
| Wrong version deployed | Replace artifact; DB unchanged if schema match |

---

## Server rollback procedure

### When schema unchanged (patch-only backend rollback)

| Step | Action |
|------|--------|
| 1 | Stop API service |
| 2 | Deploy previous backend tree / venv |
| 3 | Start service |
| 4 | Smoke test |

**Data:** No database restore needed.

### When schema changed (failed upgrade after migration)

| Step | Action |
|------|--------|
| 1 | Stop API immediately |
| 2 | Restore PostgreSQL from **pre-upgrade** verified dump |
| 3 | Deploy previous backend version |
| 4 | Confirm `alembic current` matches old head |
| 5 | Start service; verify row counts / spot checks |
| 6 | Communicate data loss window to business |

**Warning:** Restoring DB loses all writes since backup. Prefer **forward fix** if migration succeeded and business data exists post-upgrade.

---

## Database rollback detail

| Method | Supported | Notes |
|--------|-----------|-------|
| `pg_restore` / `psql` from dump | ✅ **Primary** | Pre-upgrade dump required |
| `alembic downgrade` | ❌ Not maintained | Do not rely on |
| Point-in-time recovery | ⚠️ If WAL archiving configured | Not in MVP docs |

**Verification:** Monthly restore drill to isolated instance (DEPLOY-001) ensures dumps are restorable.

---

## Desktop rollback

| Step | Action |
|------|--------|
| 1 | Uninstall or run previous installer over current |
| 2 | Confirm `userData` intact (logs, config) |
| 3 | Connect to server — ensure API version compatible |

**Artifact retention:** Store `WEBSTUDIO-IMS-Setup-{prev}.exe` on internal file share for 2+ versions.

---

## Mobile rollback

| Platform | Procedure |
|----------|-----------|
| Android | Install previous APK (must match signing certificate) |
| iOS | Reinstall previous IPA via same distribution channel |

**Note:** If server raised `min_client_version`, older clients may be **blocked** until server setting is lowered — document emergency override via admin settings or env.

---

## Configuration / secrets rollback

| Item | Rollback |
|------|----------|
| `.env` changes | Restore previous `.env` from secure backup |
| JWT secret rotation | Invalidates all sessions — users re-login |
| TLS certificates | Reinstall previous cert files |

---

## Tally sync rollback considerations

| State | Action |
|-------|--------|
| Sync half-complete after failed upgrade | `sync_in_progress` cleared on API startup (M11 engine) |
| History table from 0034 | Lost if DB restored to pre-0034 backup |
| Duplicate imports | GUID dedup prevents re-import after restore if Tally unchanged |

---

## Emergency decision tree

```
Upgrade failed?
├── Migration did NOT complete → fix SQL/migration OR restore DB + old code
├── Migration completed, API errors → forward-fix preferred
│   └── If forward-fix ETA > SLA → restore DB + old code (accept data loss)
└── API OK, client bug only → rollback client artifacts only
```

---

## Rollback readiness requirements (M12)

| Requirement | Status |
|-------------|--------|
| Pre-upgrade backup automated reminder | Documented |
| N-1 artifacts archived | ❌ No artifacts yet |
| `min_client_version` emergency procedure | Document in ops runbook |
| Incident template | Add to docs/operations in M12 |

---

## Related documents

- [UPGRADE_STRATEGY.md](./UPGRADE_STRATEGY.md)
- [DEPLOYMENT_GUIDE.md](../../deployment/DEPLOYMENT_GUIDE.md) §13–§14
- [PRODUCTION_PACKAGING_REPORT.md](./PRODUCTION_PACKAGING_REPORT.md)
