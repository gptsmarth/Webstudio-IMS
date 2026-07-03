---
Title: Disaster Recovery Guide — Production
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14D
Related Documents:
  - docs/milestones/m14/BACKUP_MANUAL.md
  - docs/milestones/m14/RESTORE_CHECKLIST.md
  - docs/milestones/m12h/RECOVERY_GUIDE.md
---

# Disaster Recovery Guide (M14D)

Production disaster recovery procedures for WEBSTUDIO IMS.

---

## 1. Recovery objectives

| Scenario | Target | Method |
|----------|--------|--------|
| Server reboot | &lt; 5 min API up | Windows Service auto-start |
| PostgreSQL failure | &lt; 15 min | Restart PG service |
| Data corruption | &lt; 2 hours | Restore from backup |
| Server PC replacement | &lt; 4 hours | Fresh machine + off-site backup |
| Bad release deploy | &lt; 1 hour | Deployment Center rollback |

---

## 2. Recovery Center

**Settings → Backup → Recovery Center**

| Metric | Meaning |
|--------|---------|
| System health | Overall status |
| Recovery readiness | ready / partial / not_ready |
| Backup status | Recent verified backup |
| Readiness score | Composite score (0–100) |

Run **Recovery wizard** (`POST /api/v1/settings/recovery/validate`) quarterly.

---

## 3. Restore (data corruption)

1. **Stop** WEBSTUDIO Server service
2. Identify last **verified** good backup
3. Recovery Center → Restore Center
4. **Preview** restore (`POST /backups/preview`)
5. Confirm emergency backup will be created
6. **Restore** entire database (`POST /backups/restore`, `confirmed: true`)
7. Restart WEBSTUDIO Server service
8. Verify login, inventory, last sale
9. If verification fails → **Rollback** (`POST /backups/rollback`)

Emergency backup filename is stored on the restore run record.

---

## 4. Fresh machine recovery

**Scenario:** New server PC or total disk loss.

### Phase A — Platform

1. Install Windows 11 Pro
2. Install PostgreSQL 16 (`ensure-postgresql.ps1`)
3. Run **WEBSTUDIO Server Setup.exe** (M14A install sequence)
4. `alembic upgrade head` to current migration
5. Configure `.env` (JWT, data root, schedulers)

### Phase B — Data

1. Copy off-site `.tar.gz` to `{DATA_ROOT}/backups`
2. Settings → Backup → **Import backup** (if needed)
3. Restore wizard → **entire_database** scope
4. Restart WEBSTUDIO Server service

### Phase C — Validate

1. `GET /settings/backups/production-validation`
2. Complete [RESTORE_CHECKLIST.md](RESTORE_CHECKLIST.md)
3. Test Tally sync (M14C)
4. Test client connectivity (M14B)

**No manual SQL editing required** — archives use data-only dumps onto migrated schema.

---

## 5. Database recovery

| Item | Detail |
|------|--------|
| Dump mode | `data_only` (current) |
| Schema | Must match `manifest.schema_version` or run migrations first |
| Tables | Full webstudio business state (inventory, sales, users, audit, Tally state) |
| Post-restore | Automatic table/count verification |

Legacy `.sql` dumps without manifest still restore with reduced validation.

---

## 6. Configuration recovery

Restored automatically from archive:

- `config/settings-registry.json` — system settings
- `config/application.env.snapshot` — non-secret env snapshot
- Manifest hashes for Tally and AI config versions

Integration **secrets** (API keys) restore from encrypted DB rows in `database.sql`.

---

## 7. Windows Service recovery

| Service | Name | Start |
|---------|------|-------|
| WEBSTUDIO API | `WEBSTUDIO Server` | Delayed auto (NSSM) |
| PostgreSQL | `postgresql-x64-16` | Automatic |

After restore:

```powershell
Restart-Service "WEBSTUDIO Server"
Get-Service "WEBSTUDIO Server", "postgresql-x64-16"
```

Install script: `infra/windows/install-webstudio-service.ps1`

---

## 8. Scheduler recovery

Schedulers persist timing in `webstudio.scheduler_runtime_state`:

| Key | Purpose |
|-----|---------|
| `backup` | Next scheduled backup |
| `tally_sync` | Tally poll interval |
| `tally_connectivity_probe` | Tally workstation probe |
| `notification_delivery` | Notifications |
| `github_release_sync` | Release catalog (optional) |

On server restart, `startup_orchestrator.restore_scheduler_state()` resumes intervals.

Env flags (production):

```env
WEBSTUDIO_BACKUP_SCHEDULER=1
WEBSTUDIO_TALLY_SCHEDULER=1
WEBSTUDIO_TALLY_CONNECTIVITY_PROBE=1
WEBSTUDIO_NOTIFICATION_SCHEDULER=1
```

---

## 9. Tally checkpoint recovery

Graceful shutdown (`stop-business-day.ps1` or service stop):

1. Waits for in-flight Tally sync (up to 15s)
2. `checkpoint_tally_sync()` finalizes open sync history
3. Persists scheduler checkpoint in `scheduler_runtime_state`

After restart, Tally sync resumes from GUID/date checkpoint — no manual re-import.

---

## 10. Release rollback

**Deployment Center** (M13) — administrator approval required.

Enterprise rollback steps:

1. Create pre-rollback safety backup
2. Stop backend / service
3. Restore database from pre-deploy backup
4. Restore configuration
5. Restore Windows service config
6. Restore backend binaries
7. Restore scheduler state
8. Restore release metadata

Implementation: `enterprise_rollback_engine.py`

Clients never contact GitHub — server remains update authority.

---

## 11. Outage quick reference

| Event | First action |
|-------|--------------|
| Server off | Power on; wait for services |
| API down | Check logs; restart WEBSTUDIO Server |
| PG down | `Start-Service postgresql-x64-16` |
| Corrupt data | Stop service → restore backup |
| Bad deploy | Deployment Center → Rollback |
| Stolen server | Fresh machine + off-site backup |

---

## 12. Validation

```http
GET /api/v1/settings/backups/production-validation
```

```powershell
.\infra\windows\validate-production-backup.ps1 -BearerToken "<jwt>"
```

Report: [BACKUP_VALIDATION_REPORT.md](BACKUP_VALIDATION_REPORT.md)

---

## 13. Escalation

Contact WEBSTUDIO engineering if:

- Restore verification fails and rollback unavailable
- Schema version mismatch blocks restore
- Backup integrity reports corruption on all archives

Preserve: backup filename, restore run ID, server logs, `manifest.json` from archive.
