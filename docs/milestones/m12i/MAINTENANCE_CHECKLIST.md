---
Title: Maintenance Checklist
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12I
---

# Maintenance Checklist

Recurring operations for WEBSTUDIO IMS in production. Aligns with [MAINTENANCE_GUIDE](../m12h/MAINTENANCE_GUIDE.md).

---

## Daily (business hours)

- [ ] Server Windows service running (or confirm auto-start after reboot)
- [ ] Desktop clients connect without errors
- [ ] Review **notifications** for failed Tally sync or backup warnings
- [ ] End of day: optional `stop-business-day.ps1` if using scripted shutdown

## Weekly

- [ ] Verify **automated backup** completed (Admin → Backup → history)
- [ ] Copy latest backup to off-site or NAS
- [ ] Review **audit log** for unusual activity
- [ ] Check disk space on server data volume (≥10% free recommended)
- [ ] Tally sync summary: imported vs skipped counts look normal

## Monthly

- [ ] Test **restore** procedure on isolated database (not production overwrite)
- [ ] Review user accounts: disable departed staff
- [ ] Rotate integration API keys if policy requires
- [ ] Apply Windows updates on server during maintenance window
- [ ] Review scheduler runtime state in Recovery Center

## Quarterly

- [ ] Full **disaster recovery** drill (backup → restore → client reconnect)
- [ ] Review custom access roles vs actual job functions
- [ ] Update desktop/mobile clients to latest approved version
- [ ] PostgreSQL `VACUUM ANALYZE` during low-traffic window (or per DBA policy)
- [ ] Review Tally mapping and company sync settings

## Per release / upgrade

- [ ] Read `RELEASE_NOTES.md` for breaking changes
- [ ] Backup database before upgrade
- [ ] Run `alembic upgrade head`; confirm Alembic version matches release manifest
- [ ] Restart Windows service
- [ ] Run Office Deployment Wizard detect pass
- [ ] Smoke test: login, inventory search, one sale, one report
- [ ] Update desktop/mobile installers on file share

## Log and crash review

- [ ] Server logs: `WEBSTUDIO_LOG_DIR` (see production `.env`)
- [ ] Crash logs: `WEBSTUDIO_CRASH_LOG_DIR`
- [ ] Desktop: crash dumps in Electron userData `crashes/`
- [ ] Escalate repeated errors with log excerpt and `version-manifest.json` commit

## Tally-specific

- [ ] Tally ERP running and reachable from server
- [ ] Company name matches Tally configuration
- [ ] Review connectivity probe status on Tally dashboard
- [ ] After Tally upgrades: run connection test from Admin

## Backup retention

- [ ] Local retention per `backup_retention_days` setting
- [ ] Off-site retention per company policy
- [ ] Secure delete of expired backups

---

## Emergency contacts template

| Role | Name | Phone | Email |
|------|------|-------|-------|
| Primary admin | | | |
| IT support | | | |
| WEBSTUDIO vendor | | | |

---

## Related documents

- [BACKUP_GUIDE](../m12h/BACKUP_GUIDE.md)
- [RESTORE_GUIDE](../m12h/RESTORE_GUIDE.md)
- [RECOVERY_GUIDE](../m12h/RECOVERY_GUIDE.md)
- [TALLY_GUIDE](../m12h/TALLY_GUIDE.md)
- [TROUBLESHOOTING_GUIDE](../m12h/TROUBLESHOOTING_GUIDE.md)
