---
Title: Restore Checklist — Production
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14D
Related Documents:
  - docs/milestones/m14/BACKUP_MANUAL.md
  - docs/milestones/m14/DISASTER_RECOVERY_GUIDE.md
  - docs/milestones/m14/BACKUP_VALIDATION_REPORT.md
---

# Restore Checklist (M14D)

Sign-off checklist for **backup, restore, and disaster recovery** validation on production (or staging drill mirroring production).

Mark each item **Pass / Fail / N/A** and attach evidence.

---

## A. Backup readiness

| ID | Check | Pass criteria | Evidence |
|----|-------|---------------|----------|
| BKP-01 | Automatic schedule | `backup_schedule` daily/weekly; `WEBSTUDIO_BACKUP_SCHEDULER=1` | Settings + `.env` |
| BKP-02 | Manual backup | POST `/settings/backups` or UI succeeds | Backup history entry |
| BKP-03 | Integrity verify | Latest archive `overall_health: healthy` | Verify API / production-validation |
| BKP-04 | Off-site copy | `.tar.gz` on USB/NAS outside server | Copy log / filename |
| BKP-05 | Retention | Old backups pruned per policy | Folder listing |
| BKP-06 | Free space | Recovery Center storage not critical | Screenshot |

---

## B. Restore procedure

| ID | Check | Pass criteria | Evidence |
|----|-------|---------------|----------|
| RST-01 | Validate archive | `POST /backups/validate` → `restore_allowed: true` | JSON response |
| RST-02 | Preview restore | `POST /backups/preview` reviewed | Screenshot / notes |
| RST-03 | Emergency backup | Pre-restore emergency archive created (full restore) | Filename recorded |
| RST-04 | Service stopped | WEBSTUDIO Server stopped during restore | Service status |
| RST-05 | Restore executed | `POST /backups/restore` completed | Restore history |
| RST-06 | Post-verify | `verification_status` success | Restore run record |
| RST-07 | Service restarted | API `/health/live` OK | curl output |
| RST-08 | Login test | Main Admin login succeeds | Screenshot |
| RST-09 | Data spot-check | Inventory / sales counts ≈ manifest | Count comparison |

---

## C. Recovery scenarios

| ID | Scenario | Pass criteria | Evidence |
|----|----------|---------------|----------|
| REC-01 | Database recovery | `database.sql` restores webstudio data | Restore drill log |
| REC-02 | Configuration recovery | Settings + company profile restored | Settings screenshot |
| REC-03 | Fresh machine | New PC restored from off-site archive only | DR drill notes |
| REC-04 | Windows Service | Service auto-starts after reboot | `Get-Service` after reboot |
| REC-05 | Scheduler recovery | `tally_sync` + `backup` rows in runtime state | DB query / API |
| REC-06 | Tally checkpoint | Sync resumes after server restart without duplicate import | Tally history |
| REC-07 | Release rollback | Deployment Center rollback documented (or drill) | Rollback run ID |

---

## D. Rollback drill (if restore verification fails)

| Step | Action | Done |
|------|--------|------|
| 1 | Note `emergency_backup_filename` from failed restore | ☐ |
| 2 | `POST /settings/backups/rollback` with emergency filename | ☐ |
| 3 | Confirm API healthy and data matches pre-restore | ☐ |
| 4 | Document incident in operator log | ☐ |

---

## E. Automated validation

```http
GET /api/v1/settings/backups/production-validation
```

**Required checks passed or warning with documented remediation:**

- `automatic_backups`
- `restore_capability`
- `database_recovery`
- `configuration_recovery`
- `backup_integrity`
- `scheduler_recovery`
- `tally_checkpoint_recovery`
- `release_rollback`

```powershell
.\infra\windows\validate-production-backup.ps1 -BearerToken "<jwt>"
```

---

## F. Annual restore drill (recommended)

1. Copy production backup to **staging** environment
2. Run full restore on staging (not production)
3. Complete sections A–C on staging
4. Record duration and issues
5. Update this checklist with drill date

---

## G. Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Store administrator | | | |
| Main Admin | | | |
| IT | | | |
| WEBSTUDIO engineer | | | |

**Overall result:** ☐ Pass — backup/DR production ready &nbsp; ☐ Fail — remediate before go-live

---

## H. Do not

- Restore to production without stopping WEBSTUDIO Server service
- Delete the only backup copy before verify passes
- Skip emergency backup on full database restore
- Run `fresh-dev.sh` or `docker compose down -v` on production without explicit approval
