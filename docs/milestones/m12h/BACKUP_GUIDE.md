---
Title: Backup Guide — WEBSTUDIO IMS
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12H
---

# Backup Guide

Protect showroom data with WEBSTUDIO enterprise backups.

---

## 1. What is backed up

Each backup archive (`.tar.gz`) contains:

| Content | Description |
|---------|-------------|
| `database.sql` | PostgreSQL `webstudio` schema data |
| `manifest.json` | Version, counts, checksum |
| Brand/product images | Managed assets |
| Settings snapshot | Non-secret configuration |
| Company assets | Logos, uploads |

---

## 2. Backup location

Default: `{WEBSTUDIO_DATA_ROOT}/backups` (e.g. `D:\WEBSTUDIO-IMS\backups`)

Configure in **Settings → Backup → Local backup folder**.

Office Deployment Wizard sets this automatically.

---

## 3. Manual backup

1. **Settings → Backup**
2. **Run manual backup**
3. Wait for success message
4. Note **Last backup** timestamp

Requires `backup:manage` permission.

---

## 4. Scheduled backup

| Setting | Options |
|---------|---------|
| Schedule | Manual, daily, weekly |
| Retention | Last N backups (default 30) |
| Storage backend | Local (NAS/cloud future-ready) |

Scheduler env: `WEBSTUDIO_BACKUP_SCHEDULER=1`

---

## 5. Off-site copies

**Recommended:** Weekly or monthly copy to:

- External USB drive (encrypted)
- NAS share
- Cloud storage (when enabled)

Store **outside** the server PC — protects against hardware theft or fire.

---

## 6. Verify backup health

**Recovery Center** shows:

- Last backup time
- Backup status (healthy / warning)
- Failed backup count

Run **Recovery wizard** validation periodically.

---

## 7. Manifest and checksum

Each archive includes SHA-256 checksum in `manifest.json`. Verification runs automatically on restore.

---

## 8. Best practices

| Practice | Why |
|----------|-----|
| Backup before upgrade | Rollback path |
| Test restore annually | Prove recoverability |
| Encrypt off-site media | Data protection |
| Document who can run backup | Accountability |

---

## 9. Related

- [Restore Guide](RESTORE_GUIDE.md)
- [Recovery Guide](RECOVERY_GUIDE.md)
- [docs/internal/BACKUP_RESTORE.md](../../internal/BACKUP_RESTORE.md) (technical)
