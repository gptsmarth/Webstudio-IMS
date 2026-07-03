---
Title: Deployment Checklist
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12I
---

# Deployment Checklist — Staging / Production

Operator checklist before bringing WEBSTUDIO IMS online in an office LAN. Complete in order.

**Reference:** [docs/milestones/m12h/DEPLOYMENT_GUIDE.md](../m12h/DEPLOYMENT_GUIDE.md)

---

## 1. Infrastructure

- [ ] Windows Server or dedicated PC meets [RUNTIME_DEPENDENCIES](../m12a/RUNTIME_DEPENDENCIES.md)
- [ ] PostgreSQL 16+ installed and reachable on LAN
- [ ] Static IP or DHCP reservation for server documented
- [ ] Firewall rules: TCP **8000** (API), **5432** (PostgreSQL LAN-only if remote admin)
- [ ] Antivirus exclusions for `WEBSTUDIO` data and log directories

## 2. Server install

- [ ] Run `WEBSTUDIO-Server-Setup.exe` (or manual install per Server Guide)
- [ ] NSSM Windows service registered (`install-webstudio-service.ps1`)
- [ ] Copy `config/env/.env.production` → server `.env`; set `JWT_SECRET` (≥32 bytes)
- [ ] Set `DATABASE_URL` to production PostgreSQL
- [ ] Run `alembic upgrade head`; verify revision `0036_tally_probe_scheduler`
- [ ] Service starts; `/health/live` returns 200

## 3. First-run wizard

- [ ] Complete setup wizard (main admin, company name)
- [ ] Run **Office Deployment Wizard** — all 10 checks reviewed
- [ ] Save deployment summary; confirm backup path and image storage path
- [ ] Recovery key printed and stored securely

## 4. Integrations

- [ ] Tally: host, company, port configured; connection test passes
- [ ] Tally sync interval and alerts configured
- [ ] AI: Gemini API key (if enrichment enabled)
- [ ] Product image storage path writable

## 5. Backup and recovery

- [ ] Manual backup succeeds from Admin → Backup
- [ ] Backup file checksum verified
- [ ] Test restore on **non-production** database clone
- [ ] Backup schedule enabled for business hours
- [ ] Off-site copy procedure documented

## 6. Client deployment

- [ ] Desktop installer distributed to workstations
- [ ] Mobile APK/IPA sideload or store build distributed
- [ ] Clients discover server via IP or mDNS (`.local`)
- [ ] Login and role-based navigation verified per user type

## 7. Security

- [ ] Default passwords changed
- [ ] Integration keys rotated from any dev values
- [ ] HTTPS/TLS configured if exposed beyond LAN (recommended for remote access)
- [ ] Audit log retention policy set

## 8. Validation

- [ ] Create test inventory item → sell → verify report
- [ ] Tally sync dry run (if enabled)
- [ ] Notification and dashboard widgets load
- [ ] Graceful service stop/start (`stop-business-day.ps1` / `start-business-day.ps1`)

## 9. Sign-off

- [ ] Deployment summary archived
- [ ] Operator trained on [ADMINISTRATOR_GUIDE](../m12h/ADMINISTRATOR_GUIDE.md)
- [ ] Support contact and escalation path documented
- [ ] Staging sign-off recorded before production cutover

---

**Rollback:** See [ROLLBACK_STRATEGY](../m12a/ROLLBACK_STRATEGY.md) and [RECOVERY_GUIDE](../m12h/RECOVERY_GUIDE.md).
