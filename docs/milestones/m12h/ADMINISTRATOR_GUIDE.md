---
Title: Administrator Guide — WEBSTUDIO IMS
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12H
Audience: Main Admin, IT administrators
---

# Administrator Guide

Guide for **Main Admin** and delegated administrators managing WEBSTUDIO IMS in a retail showroom.

---

## 1. Administrator responsibilities

| Area | Your role |
|------|-----------|
| First-time setup | Complete system setup wizard and office deployment wizard |
| Users & access | Create users, assign roles, reset passwords |
| Integrations | Tally, AI, Excel export paths |
| Backups | Schedule and verify backups; store off-site copies |
| Recovery | Run recovery wizard after outages |
| Reports | Export inventory, sales, audit reports |

---

## 2. First login

1. Install server and clients per [Installation Guide](INSTALLATION_GUIDE.md).
2. Open **WEBSTUDIO Desktop** on the admin PC.
3. Connect to server (auto-discovery or manual URL).
4. Complete **System Setup** if prompted: company profile, Main Admin account, recovery key.
5. Complete **Office Deployment Wizard** (auto-opens): detect environment, save paths, download deployment summary.

---

## 3. Settings overview

Open **Settings** from the sidebar (requires `settings:view` or higher).

| Section | Purpose |
|---------|---------|
| **General** | Company name, address, GST, timezone |
| **Security** | Session timeout, password policy, recovery key |
| **Inventory** | Default store, colours, serial prefix |
| **Sales** | Payment modes, invoice prefix |
| **Tally** | Host, company, sync interval, operational metrics |
| **Integrations** | AI provider keys and models |
| **Notifications** | Alert categories (Tally, inventory, backup) |
| **Backup** | Folder, schedule, retention, Recovery Center |

---

## 4. User management

**Path:** Settings → Users (or Admin Center)

| Task | Steps |
|------|-------|
| Add user | Create username, display name, role, initial password |
| Change role | Edit user → select access role |
| Disable user | Archive/deactivate — user cannot log in |
| Reset password | Admin reset; user changes on next login |

**Roles:** Main Admin has full access. Custom roles grant module permissions (inventory, sales, reports, Tally view, backup).

---

## 5. Tally administration

See [Tally Guide](TALLY_GUIDE.md). Administrators configure:

- Tally host (billing laptop hostname)
- Company name (exact match)
- Sync interval (60–3600 seconds)
- Enable/disable sync and alerts

**Operators never see:** GUID, MasterID, AlterID, or raw XML.

---

## 6. Backup administration

See [Backup Guide](BACKUP_GUIDE.md).

| Action | Frequency |
|--------|-----------|
| Automatic backup | Per schedule in Settings → Backup |
| Manual backup | Before upgrades or major changes |
| Off-site copy | Weekly/monthly to USB or NAS |

Verify **Last backup** timestamp in Recovery Center.

---

## 7. Reports and audit

| Report | Use |
|--------|-----|
| Inventory | Stock by location, brand, status |
| Sales | Invoice history, filters by date |
| Audit log | Who changed what and when |
| Notifications | Tally sync issues, duplicates, missing serials |

Export to Excel/PDF where available.

---

## 8. Security checklist

- [ ] Recovery key stored offline (safe, not on server PC)
- [ ] Strong JWT secret on server (installer-generated)
- [ ] Session timeout ≤ 15 minutes for shared PCs
- [ ] Unused accounts disabled
- [ ] Firewall allows API only from store LAN
- [ ] Backups tested with restore drill annually

---

## 9. Related guides

- [Employee Guide](EMPLOYEE_GUIDE.md) — staff training
- [Maintenance Guide](MAINTENANCE_GUIDE.md) — upgrades
- [Recovery Guide](RECOVERY_GUIDE.md) — outages
- [Troubleshooting Guide](TROUBLESHOOTING_GUIDE.md) — common issues
