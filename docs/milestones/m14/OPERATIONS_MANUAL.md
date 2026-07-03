---
Title: Operations Manual — WEBSTUDIO IMS
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14H
Audience: Main Admin, IT operators, store managers
Related Documents:
  - docs/milestones/m14/ADMINISTRATOR_MANUAL.md
  - docs/milestones/m14/MAINTENANCE_GUIDE.md
---

# Operations Manual (M14H)

Day-to-day and planned-change operations for **WEBSTUDIO IMS** in production — deployment, updates, rollback, backups, Tally sync, and incident response.

---

## 1. Daily operations

### 1.1 Business-hours checklist

| Time | Task | Owner |
|------|------|-------|
| Opening | Power on server PC; confirm **WEBSTUDIO Server** service Running | IT |
| Opening | Start Tally on billing PC with company books open | Accounts |
| Opening | Confirm desktop toolbar shows **Connected** | Staff |
| During day | Monitor Tally Sync Health on dashboard | Admin |
| Closing | Graceful shutdown per business-hours guide | IT |

**Reference:** [m12b/BUSINESS_HOURS_DEPLOYMENT_GUIDE.md](../m12b/BUSINESS_HOURS_DEPLOYMENT_GUIDE.md)

### 1.2 Health checks

```powershell
# From any LAN workstation
Invoke-RestMethod http://<server-ip>:8000/health/live
Invoke-RestMethod http://<server-ip>:8000/health/ready
```

| Endpoint | Pass |
|----------|------|
| `/health/live` | HTTP 200 — process alive |
| `/health/ready` | Database connected, migrations current |
| `/api/v1/version` | Matches installed release bundle |

---

## 2. Deployment

### 2.1 Server deployment (initial)

Initial server deployment is covered in the [Administrator Manual](ADMINISTRATOR_MANUAL.md) § Installation. After install, run commissioning phases A–F in [PRODUCTION_COMMISSIONING_GUIDE.md](PRODUCTION_COMMISSIONING_GUIDE.md).

### 2.2 Client deployment

| Platform | Artifact | Guide |
|----------|----------|-------|
| Windows desktop | `WEBSTUDIO Desktop Setup.exe` | [DESKTOP_DEPLOYMENT_GUIDE.md](DESKTOP_DEPLOYMENT_GUIDE.md) |
| macOS desktop | `WEBSTUDIO Desktop.dmg` | [DESKTOP_DEPLOYMENT_GUIDE.md](DESKTOP_DEPLOYMENT_GUIDE.md) |
| Android | `WEBSTUDIO.apk` (sideload) | [MOBILE_DEPLOYMENT_GUIDE.md](MOBILE_DEPLOYMENT_GUIDE.md) |
| iOS | TestFlight / enterprise distribution | [MOBILE_DEPLOYMENT_GUIDE.md](MOBILE_DEPLOYMENT_GUIDE.md) |

**Rules:**

- Clients download updates from **WEBSTUDIO Server** — never from GitHub directly.
- Server must be commissioned before client rollout.
- Validate with [CLIENT_ACCEPTANCE_CHECKLIST.md](CLIENT_ACCEPTANCE_CHECKLIST.md).

### 2.3 Office deployment wizard

Run once after first server start (auto-opens on Main Admin desktop):

1. Detect server environment (IP, paths, PostgreSQL).
2. Save discovery URLs for all clients.
3. Export deployment summary for IT records.

Re-run if server IP or backup paths change.

### 2.4 Deployment validation

```http
GET /api/v1/deployment/client-validation
GET /api/v1/deployment/production-acceptance
Authorization: Bearer <network-admin-token>
```

Or:

```powershell
.\infra\windows\validate-production-network.ps1 -BearerToken "<token>"
```

---

## 3. Updates

### 3.1 Release authority

| Source | Role |
|--------|------|
| WEBSTUDIO Server release catalog | **Authoritative** — clients check here |
| `VERSION.json` / `GET /api/v1/version` | Installed version truth |
| Deployment Center (desktop) | Administrator-approved upgrades |

**Reference:** [m13/ENTERPRISE_VERSION_MANAGEMENT_REPORT.md](../m13/ENTERPRISE_VERSION_MANAGEMENT_REPORT.md)

### 3.2 Server update procedure

| Step | Action |
|------|--------|
| 1 | Read `RELEASE_NOTES.md` in new bundle |
| 2 | **Manual backup** (Settings → Backup → Create now) |
| 3 | Verify backup checksum in Recovery Center |
| 4 | Stop **WEBSTUDIO Server** service |
| 5 | Run new `WEBSTUDIO Server Setup.exe` or replace files per release instructions |
| 6 | `alembic upgrade head` (installer usually runs this) |
| 7 | Start service |
| 8 | `GET /health/ready` — confirm migrations |
| 9 | Upgrade all clients to matching version |
| 10 | Run production validation scripts |

### 3.3 Client updates

1. Server publishes new version to release catalog.
2. Desktop/mobile **Check for updates** (or auto-prompt).
3. Client downloads from server API `/api/v1/client-updates/check`.
4. Install after server upgrade completes.

**Minimum versions** enforced by server (`min_desktop_version`, `min_mobile_version`).

### 3.4 Deployment Center (desktop)

Main Admin uses **Deployment Center** for:

- View current and available releases
- Download release artifacts for offline install
- **Approve** server upgrade (administrator approval required)
- View compatibility matrix

---

## 4. Rollback

Rollback returns the system to a **previous known-good release** when an upgrade fails verification.

### 4.1 When to rollback

| Trigger | Action |
|---------|--------|
| `/health/ready` fails after upgrade | Rollback before staff use |
| Migration error in logs | Rollback; contact WEBSTUDIO support |
| Client–server version mismatch | Rollback server or complete client upgrade |
| Post-restore verification fails | Emergency backup rollback |

### 4.2 Server release rollback

**Desktop UI:** Deployment Center → Rollback (Main Admin approval)

**API:**

```http
POST /api/v1/deployment/center/rollback
Authorization: Bearer <main-admin-token>
```

Rollback engine steps (automatic):

1. Create emergency backup of current state
2. Restore previous release files from catalog
3. Revert database if release includes downgrade path
4. Record permanent history (`GET /api/v1/deployment/center/rollback/history`)

### 4.3 Database / backup rollback

If a **restore** produces bad data:

```http
POST /api/v1/settings/backups/rollback
```

Uses emergency pre-restore archive. See [DISASTER_RECOVERY_GUIDE.md](DISASTER_RECOVERY_GUIDE.md).

### 4.4 Rollback checklist

| # | Item |
|---|------|
| 1 | Notify staff — system read-only or offline |
| 2 | Confirm emergency backup exists |
| 3 | Execute rollback via Deployment Center |
| 4 | Verify `/health/ready` and sample inventory search |
| 5 | Re-deploy matching client versions |
| 6 | Document incident in handover log |

---

## 5. Backups

### 5.1 Backup types

| Type | Trigger | Contents |
|------|---------|----------|
| **Scheduled** | Cron per Settings → Backup | PostgreSQL dump + manifest + config snapshot |
| **Manual** | Admin before upgrades/changes | Same as scheduled |
| **Emergency** | Pre-restore / pre-rollback | Automatic safety copy |

### 5.2 Configure backups

**Settings → Backup:**

| Setting | Recommended production |
|---------|------------------------|
| Folder | `D:\WEBSTUDIO-IMS\backups` or dedicated drive |
| Schedule | Daily after business hours |
| Retention | Last 30 (or per policy) |
| Off-site copy | Weekly USB/NAS |

Enable scheduler: `WEBSTUDIO_BACKUP_SCHEDULER=1` in `.env`.

### 5.3 Operational procedures

| Procedure | Steps |
|-----------|-------|
| **Create manual backup** | Settings → Backup → Create now → wait for success |
| **Verify backup** | Recovery Center → select archive → Verify |
| **Restore (drill)** | Recovery Center → Preview → Restore (staging first) |
| **Off-site copy** | Copy `.zip` archive to external media |

### 5.4 Backup validation

```powershell
.\infra\windows\validate-production-backup.ps1 -BearerToken "<token>"
```

```http
GET /api/v1/settings/backups/production-validation
```

**Guides:** [BACKUP_MANUAL.md](BACKUP_MANUAL.md) · [DISASTER_RECOVERY_GUIDE.md](DISASTER_RECOVERY_GUIDE.md) · [RESTORE_CHECKLIST.md](RESTORE_CHECKLIST.md)

### 5.5 Backup security

- Archives are **unencrypted** by default — restrict folder ACLs to administrators.
- Store off-site copies on encrypted media.
- Integration keys included in dump (encrypted in DB); AI keys excluded from restore by default.

---

## 6. Tally operations

WEBSTUDIO IMS imports **sales vouchers** from Tally ERP 9 via read-only XML export. IMS never writes back to Tally books.

### 6.1 Daily Tally checklist

| # | Check |
|---|-------|
| 1 | Tally running on billing PC with company open |
| 2 | XML port **9000** enabled in Tally |
| 3 | Settings → Tally → **Test Connection** succeeds |
| 4 | Dashboard **Tally Sync Health** = Healthy |
| 5 | Last sync timestamp updated after new invoices |

### 6.2 Configuration

| Setting | Notes |
|---------|-------|
| Host | Billing laptop hostname or IP (LAN) |
| Port | `9000` (default) |
| Company name | **Exact match** to Tally company |
| Sync interval | 60–3600 seconds |
| Enable sync | Toggle in Settings → Tally |

### 6.3 Manual sync

- **Settings → Tally → Sync Now**, or
- Dashboard → Tally card → Sync Now

Incremental sync uses voucher GUID checkpoint — duplicates are skipped automatically.

### 6.4 Common operational outcomes

| Outcome | Meaning | Action |
|---------|---------|--------|
| Imported | Serial matched and marked sold | None |
| Already sold | Duplicate GUID or prior sale | None — expected |
| Missing serial | Serial not in inventory | Receive item or manual sale |
| Missing model | Product model not in catalogue | Add brand/model |
| Offline | Tally PC unreachable | Start Tally; check LAN |

### 6.5 Tally validation

```powershell
.\infra\windows\validate-production-tally.ps1 -BearerToken "<token>"
```

**Guides:** [TALLY_PRODUCTION_GUIDE.md](TALLY_PRODUCTION_GUIDE.md) · [TALLY_VALIDATION_CHECKLIST.md](TALLY_VALIDATION_CHECKLIST.md) · [XML_VERIFICATION_GUIDE.md](XML_VERIFICATION_GUIDE.md)  
**Architecture:** [ADR-0011-tally-integration-strategy.md](../../adr/ADR-0011-tally-integration-strategy.md)

---

## 7. Troubleshooting (operations)

Quick symptom resolution during business hours. For preventive and deep diagnostics, see [MAINTENANCE_GUIDE.md](MAINTENANCE_GUIDE.md).

### 7.1 Connection

| Symptom | Fix |
|---------|-----|
| Desktop **Offline** | Start server service; check Wi‑Fi/VLAN |
| Server not in discovery list | Use manual URL `http://<ip>:8000` |
| Works on one PC only | Clear saved URL; rediscover |

### 7.2 Authentication

| Symptom | Fix |
|---------|-----|
| Invalid credentials | Admin password reset |
| Account locked | Wait lockout period (Settings → Security) |
| Session expired | Re-login |
| Setup incomplete | Complete Setup Wizard |

### 7.3 Service failures

```powershell
Get-Service "WEBSTUDIO Server"
Restart-Service "WEBSTUDIO Server"
Get-Content D:\WEBSTUDIO-IMS\logs\webstudio-api.log -Tail 50
```

| Log pattern | Likely cause |
|-------------|--------------|
| `ConfigurationError` JWT | Weak `JWT_SECRET` in production |
| `connection refused` PostgreSQL | PG service stopped |
| `alembic` migration | Run `alembic upgrade head` |

### 7.4 Tally sync

| Symptom | Fix |
|---------|-----|
| Sync Health Offline | Start Tally PC |
| Zero imports | Fix company name spelling |
| Serial not imported | Receive inventory first |

### 7.5 Backup / restore

| Symptom | Fix |
|---------|-----|
| Backup failed | Free disk space on data root |
| Checksum error | Use older verified archive |
| Restore hung | Check PostgreSQL service; review logs |

**Extended guide:** [m12h/TROUBLESHOOTING_GUIDE.md](../m12h/TROUBLESHOOTING_GUIDE.md)

---

## 8. User acceptance

Before declaring go-live, complete [USER_ACCEPTANCE_CHECKLIST.md](USER_ACCEPTANCE_CHECKLIST.md) with store staff sign-off.

---

## 9. Operator scripts (Windows server)

| Script | Purpose |
|--------|---------|
| `configure-firewall.ps1` | LAN firewall rules |
| `validate-production-network.ps1` | M14B networking |
| `validate-production-backup.ps1` | M14D backup |
| `validate-production-tally.ps1` | M14C Tally |
| `validate-production-certification.ps1` | M14G certification |
| `install-webstudio-service.ps1` | Service registration |
| `ensure-postgresql.ps1` | PostgreSQL health |

All scripts: `D:\WEBSTUDIO-IMS\infra\windows\`
