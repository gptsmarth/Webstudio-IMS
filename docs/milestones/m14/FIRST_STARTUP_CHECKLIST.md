---
Title: WEBSTUDIO IMS — First Startup Checklist
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14A
Related Documents:
  - docs/milestones/m14/INSTALLATION_MANUAL.md
  - docs/milestones/m14/PRODUCTION_COMMISSIONING_GUIDE.md
---

# WEBSTUDIO IMS — First Startup Checklist

Use this checklist for the **first cold start** of a production server and **first client connection**. Check items in order; do not skip security steps.

**Site:** _________________________  
**Server IP:** _____________________  
**Date:** _________________________  
**Operator:** ______________________

---

## Section 1 — Physical & OS (before power-on)

- [ ] UPS connected and tested
- [ ] LAN cable connected (or Wi‑Fi documented if applicable)
- [ ] Windows 11 Pro installed and updated
- [ ] Computer name set: _________________________
- [ ] Static IP / DHCP reservation: _________________________
- [ ] Local Administrator password secured

---

## Section 2 — Database layer

- [ ] PostgreSQL 16 service name: `postgresql-x64-16` (or _____________)
- [ ] PostgreSQL service **Running**
- [ ] Database `webstudio` exists
- [ ] Application DB user configured (not superuser)
- [ ] `ensure-postgresql.ps1` exits without error

---

## Section 3 — WEBSTUDIO Server install

- [ ] `WEBSTUDIO Server Setup.exe` executed as Administrator
- [ ] Install root `D:\WEBSTUDIO-IMS` populated
- [ ] Python venv at `D:\WEBSTUDIO-IMS\venv\Scripts\python.exe`
- [ ] `.env` file at `D:\WEBSTUDIO-IMS\config\env\.env`
- [ ] `JWT_SECRET` is unique (not template placeholder)
- [ ] `APP_ENV=production`
- [ ] `DATABASE_URL` points to production database

---

## Section 4 — Windows Service

- [ ] Service `WEBSTUDIO Server` registered (NSSM)
- [ ] Startup type: **Automatic (Delayed Start)**
- [ ] Service status: **Running**
- [ ] Logs created: `D:\WEBSTUDIO-IMS\logs\webstudio-api.log`
- [ ] Service recovery configured (restart on failure)

```powershell
Get-Service "WEBSTUDIO Server"
```

---

## Section 5 — Database migrations

- [ ] `alembic upgrade head` completed without error
- [ ] Alembic head: _________________________ (expect `0042_deployment_monitoring` or release manifest value)

```sql
SELECT version_num FROM webstudio.alembic_version;
```

---

## Section 6 — First API health check

From LAN admin PC:

- [ ] `GET http://<server>:8000/health/live` → **200**
- [ ] `GET http://<server>:8000/health/ready` → database **ok**
- [ ] `GET http://<server>:8000/api/v1/setup/status` → `system_initialized: false` (before wizard)

---

## Section 7 — Schedulers (automatic on service start)

Verify env flags (service + `.env`):

- [ ] `WEBSTUDIO_TALLY_SCHEDULER=1`
- [ ] `WEBSTUDIO_BACKUP_SCHEDULER=1`
- [ ] `WEBSTUDIO_NOTIFICATION_SCHEDULER=1`
- [ ] `WEBSTUDIO_MAINTENANCE_SCHEDULER=1`

Verify persistence table (after ~1 min uptime):

- [ ] Rows exist in `webstudio.scheduler_runtime_state` for `backup`, `tally_sync`, `notification_delivery`

---

## Section 8 — Optional pre-wizard configuration

- [ ] AI keys in `.env` if using enrichment at go-live (`GEMINI_API_KEY`, etc.)
- [ ] `WEBSTUDIO_DATA_ROOT` matches install root (no surrounding quotes)
- [ ] `{WEBSTUDIO_DATA_ROOT}\assets\product-images` exists and is writable by the service account
- [ ] Sample product image loads: authenticated
      `GET /api/v1/product-images/proxy?url=/assets/product-images/{model-id}.jpg` → HTTP 200
- [ ] Firewall rule: TCP 8000 from office subnet

---

## Section 9 — First administrator & Setup Wizard

On **WEBSTUDIO Desktop** (admin PC):

- [ ] Desktop installer run; app launches
- [ ] Server discovered (mDNS) or URL entered: `http://____________:8000`
- [ ] Setup Wizard shown (not login screen)
- [ ] **Step 1:** Organization name entered
- [ ] **Step 2:** Main Admin account created
- [ ] **Step 3:** Recovery key displayed
- [ ] Recovery key copied to offline secure storage
- [ ] Recovery key acknowledgment confirmed
- [ ] `GET /api/v1/setup/status` → `system_initialized: true`
- [ ] Login as Main Admin succeeds

**Recovery key storage location (do not write key here):** _________________________

---

## Section 10 — Post-wizard administrator tasks

- [ ] Change default backup schedule if not `manual`
- [ ] Configure Tally (if go-live requires): host / company / enable
- [ ] Configure AI enrichment (optional): Settings → Integrations
- [ ] Create integration API keys (only if needed)
- [ ] Create additional users / roles per policy
- [ ] Run first manual backup and verify

---

## Section 11 — Sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| IT operator | | | |
| Main Admin | | | |
| Manager | | | |

---

## Quick reference commands

```powershell
# Service
Get-Service "WEBSTUDIO Server"
Restart-Service "WEBSTUDIO Server"

# Logs
Get-Content D:\WEBSTUDIO-IMS\logs\webstudio-api.log -Tail 50

# Migrations (upgrade only)
cd D:\WEBSTUDIO-IMS\apps\backend
D:\WEBSTUDIO-IMS\venv\Scripts\python.exe -m alembic upgrade head
```

```bash
# Health (from LAN)
curl -s http://<server-ip>:8000/health/ready
curl -s http://<server-ip>:8000/api/v1/setup/status
curl -s http://<server-ip>:8000/api/v1/version
```

---

## Failures — stop and escalate

Do **not** proceed to staff rollout if any of the following occur:

- `/health/ready` database check fails
- Service enters restart loop
- Setup Wizard cannot complete or `system_initialized` stays false
- Recovery key not stored offline
- Alembic migration error

See [INSTALLATION_MANUAL.md](INSTALLATION_MANUAL.md) troubleshooting and [m12h/TROUBLESHOOTING_GUIDE.md](../m12h/TROUBLESHOOTING_GUIDE.md).
