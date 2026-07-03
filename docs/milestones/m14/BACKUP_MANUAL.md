---
Title: Backup Manual — Production
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14D
Related Documents:
  - docs/milestones/m14/DISASTER_RECOVERY_GUIDE.md
  - docs/milestones/m14/RESTORE_CHECKLIST.md
  - docs/milestones/m12h/BACKUP_GUIDE.md
  - docs/internal/BACKUP_RESTORE.md
---

# Backup Manual (M14D)

Production operator guide for **WEBSTUDIO IMS enterprise backups** on the dedicated server PC.

---

## 1. What is protected

Each `.tar.gz` archive contains:

| Component | Path in archive |
|-----------|-----------------|
| PostgreSQL data | `database.sql` (webstudio schema, data-only) |
| Manifest | `manifest.json` (checksum, counts, versions) |
| Settings snapshot | `config/settings-registry.json` |
| Environment snapshot | `config/application.env.snapshot` (non-secret) |
| Brand / product images | `assets/*` |
| Company uploads | `assets/company/`, `assets/uploads/` |

Format version: **2.1** (`data_only` dump mode for portable disaster recovery).

---

## 2. Backup location

| Setting | Default |
|---------|---------|
| Folder | `{WEBSTUDIO_DATA_ROOT}/backups` (e.g. `D:\WEBSTUDIO-IMS\backups`) |
| Configure | Settings → Backup → Local backup folder |

Ensure the volume has adequate free space (Recovery Center shows estimates).

---

## 3. Automatic backups

### Server environment

```env
WEBSTUDIO_BACKUP_SCHEDULER=1
```

### Schedule settings

| Setting | Options |
|---------|---------|
| `backup_schedule` | `manual`, `daily`, `weekly` |
| `backup_retention_policy` | `last_30` (default), custom count |
| `backup_storage_backend` | `local` (NAS/cloud stubs future-ready) |

The backup scheduler polls every **15 minutes** and runs when the schedule window is due.

### Verification

```http
GET /api/v1/settings/backups/production-validation
```

Check `automatic_backups` status is **passed**.

---

## 4. Manual backups

**When to run:**

- Before software upgrade or Deployment Center release
- Before restore drill
- Before major data changes
- Weekly/monthly for **off-site copy**

**Steps:**

1. Settings → Backup
2. **Run manual backup**
3. Wait for success notification
4. Confirm **Last backup** timestamp updates
5. Optional: **Verify** on the archive in Backup Admin

**API:**

```http
POST /api/v1/settings/backups
Content-Type: application/json

{"backup_type": "full"}
```

Requires `backup:manage` permission.

---

## 5. Backup integrity

### Automatic

Each backup run records checksum SHA-256 in the database and manifest.

### Manual verify

1. Settings → Backup → Admin → select archive
2. **Verify integrity**

Or:

```http
POST /api/v1/settings/backups/{filename}/verify
```

### Production validation

The `backup_integrity` check in production validation runs integrity verification on the **latest** archive.

---

## 6. Retention

Old backups are pruned per retention policy after successful new backups.

| Practice | Recommendation |
|----------|----------------|
| On-server retention | 30 backups (default) |
| Off-site copies | Weekly USB / NAS / cloud |
| Pre-upgrade | Manual backup + verify |

---

## 7. Off-site copies

**Critical:** Store copies **outside** the server PC.

1. Copy latest `.tar.gz` to encrypted USB or NAS
2. Record date and filename in operator log
3. Test restore annually (see [RESTORE_CHECKLIST.md](RESTORE_CHECKLIST.md))

---

## 8. Notifications

Backup events emit in-app notifications when:

- `backup_alerts_enabled` = true
- `system_alerts_enabled` = true

Alerts cover: backup completed, failed, low storage, restore started/completed/failed.

---

## 9. Permissions

| Permission | Capability |
|------------|------------|
| `backup:view` | View status, Recovery Center |
| `backup:manage` | Create, verify, configure |
| `restore:view` | Preview, history |
| `restore:execute` | Restore, rollback |

Main Admin has all permissions by default.

---

## 10. Production validation

```powershell
cd C:\WEBSTUDIO\ims\infra\windows
.\validate-production-backup.ps1 -BearerToken "<admin-jwt>"
```

```http
GET /api/v1/settings/backups/production-validation
```

---

## 11. Related

- [DISASTER_RECOVERY_GUIDE.md](DISASTER_RECOVERY_GUIDE.md) — outages and full DR
- [RESTORE_CHECKLIST.md](RESTORE_CHECKLIST.md) — restore sign-off
- [docs/internal/BACKUP_RESTORE.md](../../internal/BACKUP_RESTORE.md) — technical reference
