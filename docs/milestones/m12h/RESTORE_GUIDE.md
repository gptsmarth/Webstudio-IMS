---
Title: Restore Guide — WEBSTUDIO IMS
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12H
---

# Restore Guide

Restore WEBSTUDIO IMS from a backup archive. **Main Admin / restore permission required.**

---

## 1. When to restore

| Scenario | Restore type |
|----------|--------------|
| Data corruption | Full restore from last good backup |
| Wrong deletion | Full restore (data loss since backup) |
| Disaster recovery | Full restore on new server hardware |
| Settings only | Partial (advanced — contact engineering) |

---

## 2. Before restore

1. **Stop** WEBSTUDIO Server service (prevents writes during restore)
2. Identify backup file in `backups/` folder
3. Note backup date — all changes after that date will be lost
4. Optional: run **emergency backup** of current state (Recovery wizard)

---

## 3. Restore wizard (desktop)

1. **Settings → Backup → Open Restore Center**
2. Select backup file from list
3. **Restore wizard** — follow steps:
   - Choose scope (full recommended)
   - Confirm warnings
   - Wait for completion
4. Restart server service
5. Verify login, inventory count, last sale date

---

## 4. Verification after restore

| Check | Expected |
|-------|----------|
| Login | Main Admin succeeds |
| Inventory count | Matches manifest counts (~) |
| Tally sync | Resumes on next interval |
| Users | Present from backup time |
| Audit log | History to backup point |

**Restore verification** status shown in restore history.

---

## 5. Schema compatibility

Current backups use **data-only** dumps — restore assumes schema matches backup's `schema_version`.

**Rule:** Run `alembic upgrade head` on target server **before** restore if upgrading hardware with newer release.

---

## 6. Legacy SQL dumps

Older `.sql` files without manifest still restore but skip extended validation.

---

## 7. Failed restore

| Symptom | Action |
|---------|--------|
| Checksum failed | Re-copy backup file; try older backup |
| Schema mismatch | Upgrade migrations; retry |
| Partial restore | Do not use system — restore again from clean backup |

Contact engineering with `manifest.json` from archive.

---

## 8. Related

- [Backup Guide](BACKUP_GUIDE.md)
- [Recovery Guide](RECOVERY_GUIDE.md)
- Desktop **Recovery Wizard** in Settings → Backup
