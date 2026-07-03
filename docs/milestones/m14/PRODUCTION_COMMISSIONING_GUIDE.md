---
Title: WEBSTUDIO IMS — Production Commissioning Guide
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14A
Related Documents:
  - docs/milestones/m14/INSTALLATION_MANUAL.md
  - docs/milestones/m14/FIRST_STARTUP_CHECKLIST.md
  - docs/milestones/m12i/DEPLOYMENT_CHECKLIST.md
---

# WEBSTUDIO IMS — Production Commissioning Guide

Commissioning turns a **successfully installed** server into an **operational production system** ready for staff use. Perform after [INSTALLATION_MANUAL.md](INSTALLATION_MANUAL.md) steps 1–14.

**Roles:** IT operator (server), Main Admin (wizard + settings), Manager (business sign-off).

---

## Commissioning phases

```
Install complete (14A manual)
        ↓
Phase A — Infrastructure sign-off
        ↓
Phase B — Service & API sign-off
        ↓
Phase C — Security & backup sign-off
        ↓
Phase D — Integration sign-off (Tally, AI)
        ↓
Phase E — Client rollout readiness
        ↓
Phase F — Go-live approval
```

---

## Phase A — Infrastructure sign-off

| Check | Procedure | Pass criteria |
|-------|-----------|---------------|
| Server identity | Document hostname, IP, install root | Record in handover pack |
| Time sync | `w32tm /query /status` | NTP synchronized |
| Disk space | Check `D:\` free ≥20% | Startup `storage` check ok |
| Firewall | TCP 8000 from LAN only | External WAN blocked |
| UPS | Test graceful stop script | [m12b/BUSINESS_HOURS_DEPLOYMENT_GUIDE.md](../m12b/BUSINESS_HOURS_DEPLOYMENT_GUIDE.md) |

---

## Phase B — Service & API sign-off

Run from admin workstation on LAN.

| # | Check | Command / endpoint | Expected |
|---|-------|-------------------|----------|
| 1 | Service running | `Get-Service "WEBSTUDIO Server"` | Running |
| 2 | Liveness | `GET /health/live` | HTTP 200 |
| 3 | Readiness | `GET /health/ready` | DB ok, migrations ok |
| 4 | Version | `GET /api/v1/version` | Matches release bundle |
| 5 | Discovery | `GET /api/v1/discovery/health` | `online: true` |
| 6 | Capabilities | `GET /api/v1/capabilities` | Modules listed |
| 7 | Schedulers | SQL on `scheduler_runtime_state` | Core keys present |
| 8 | Logs | Tail `webstudio-api.log` | No repeating ERROR after 5 min |

**Startup orchestration checks** (in logs on service start):

- `postgresql` → ok
- `storage` → ok
- `configuration` → ok (or `warning` if wizard pending — resolved after step 14)
- `ai_configuration` → ok or warning (keys optional)
- `tally_configuration` → ok or warning until Tally configured

---

## Phase C — Security & backup sign-off

| Check | Procedure | Pass |
|-------|-----------|------|
| JWT secret | Verify not default; ≥32 bytes | Pass |
| Production env | `APP_ENV=production` | Pass |
| Main Admin only | No extra users before policy defined | Pass |
| Recovery key | Offline copy confirmed by Main Admin | Pass |
| Backup folder | `D:\WEBSTUDIO-IMS\backups` writable | Pass |
| Manual backup | Settings → Backup → Run now | Archive created |
| Backup verify | Verify checksum in admin UI | Valid |
| Restore drill (staging) | Optional pre-go-live | Document result |

**Reference:** [m12h/BACKUP_GUIDE.md](../m12h/BACKUP_GUIDE.md), [m11/SECURITY_QA_REPORT.md](../m11/SECURITY_QA_REPORT.md)

---

## Phase D — Integration sign-off

### Tally ERP 9

| Step | Action |
|------|--------|
| 1 | Enable XML on Tally billing PC (port 9000) |
| 2 | Settings → Tally: host, company, enable sync |
| 3 | Set sync interval (≥300s recommended) |
| 4 | Run manual sync or wait for scheduler |
| 5 | Verify **Tally Sync Health** dashboard |

### AI enrichment (optional)

| Step | Action |
|------|--------|
| 1 | Add provider key in `.env` or Settings |
| 2 | Enable enrichment; set provider chain |
| 3 | Test AI from Settings |
| 4 | Add one test laptop with AI assist |

### Integration API keys (optional)

Create only if external integrations are in scope for go-live.

---

## Phase E — Client rollout readiness

| Client | Commissioning action |
|--------|---------------------|
| Admin desktop | Installed; connected; wizard complete; login verified |
| Floor desktops | Installer ready; server URL documented |
| Android | APK distributed; sideload policy agreed |
| iOS | App Store / TestFlight per release channel |

**Office deployment wizard** (optional): Settings → Backup → Office deployment for multi-location metadata.

---

## Phase F — Go-live approval

| Role | Sign-off |
|------|----------|
| IT | Phases A + B complete |
| Main Admin | Phases C + D complete; recovery key secured |
| Manager | Sample business workflow tested (sale → inventory) |
| Engineering | Release manifest archived; version recorded |

Record sign-off in [PRODUCTION_DEPLOYMENT_REPORT.md](PRODUCTION_DEPLOYMENT_REPORT.md) appendix or customer handover log.

---

## Smoke test script (minimum)

1. Login as Main Admin  
2. Create one location  
3. Add one inventory item (manual or AI-assisted)  
4. Record one sale  
5. Confirm audit log entry  
6. Run backup; confirm timestamp  
7. Restart `WEBSTUDIO Server` service  
8. Confirm clients reconnect within 2 minutes  
9. Confirm schedulers resume (check Deployment Center analytics or `scheduler_runtime_state`)

---

## Rollback during commissioning

If commissioning fails before go-live:

1. `Stop-Service "WEBSTUDIO Server"`
2. Restore PostgreSQL from pre-commissioning backup
3. Re-run installer or previous release bundle per [m12a/ROLLBACK_STRATEGY.md](../m12a/ROLLBACK_STRATEGY.md)
4. Document failure; do not mark Phase F complete

For post-go-live rollback use **Deployment Center → Rollback** (M13F) with administrator approval.

---

## Next milestone

After commissioning sign-off, proceed to **14B — Production configuration** (fine-tune env, schedules, release channel) or **14D — Production validation** per [README.md](README.md).
