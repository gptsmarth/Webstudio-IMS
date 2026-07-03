---
Title: Customer Installation Walkthrough
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12J
---

# Customer Installation Walkthrough

Narrative walkthrough for **PRECISION LAPTOPS** — a fictional new customer with a dedicated server, desktop admin PC, two mobile devices, and Tally on a Lenovo laptop.

---

## Act 1 — Server room (Dedicated Server PC)

### 1.1 Unbox and prepare

The integrator installs Windows 11 Pro on the dedicated server (`192.168.1.10`). PostgreSQL 16 is installed locally. The shop uses a flat `/24` LAN (`192.168.1.0/24`).

### 1.2 Install WEBSTUDIO Server

1. Verify release checksums: `shasum -a 256 -c checksums.sha256`
2. Run **`WEBSTUDIO Server Setup.exe`** (or manual install per [INSTALLATION_GUIDE](../m12h/INSTALLATION_GUIDE.md))
3. Default root: `D:\WEBSTUDIO-IMS`

### 1.3 Configure Windows Service

The installer (or `install-webstudio-service.ps1`) registers **WEBSTUDIO Server** via NSSM:

- **Start type:** Automatic (Delayed Start) — boots after PostgreSQL
- **Recovery:** Restart on failure
- **Migrations:** `alembic upgrade head` during install
- **Schedulers:** Tally, backup, notifications enabled via environment

Verify:

```powershell
sc query "WEBSTUDIO Server"
curl http://localhost:8000/health/live
```

### 1.4 Initialize database

Fresh PostgreSQL database `webstudio` is created. Migrations apply schema through head `0036_tally_probe_scheduler`.

---

## Act 2 — First boot (Admin Desktop Client)

### 2.1 Install desktop

1. Run **`WEBSTUDIO Desktop Setup.exe`** on the admin PC
2. Launch from Start Menu
3. Server URL: `http://192.168.1.10:8000` (or auto-discovered via mDNS)

### 2.2 Setup company

1. Open **System Setup** (first visit — server reports `system_initialized: false`)
2. Enter:
   - Company: **PRECISION LAPTOPS**
   - Main Admin: Store Owner / `mainadmin`
   - Strong password
3. **Recovery key** is displayed once — print and store in safe
4. Confirm recovery key to complete initialization

### 2.3 Office Deployment Wizard

1. **Detect** — 10 checks: network, PostgreSQL, Windows service, API, backup path, image storage, AI, Tally, firewall, ports
2. **Apply** — backup folder and image storage paths saved automatically
3. **Complete** — summary shows `client_connection_url` for floor staff

---

## Act 3 — Floor staff (Android + iPhone)

### 3.1 Android phone

1. Install APK from shared drive
2. Enter server URL from deployment summary
3. Log in as salesperson
4. Verify **sync state** loads and **search** returns results

### 3.2 iPhone

Same flow as Android — WEBSTUDIO mobile uses identical API surface (`/api/v1/version`, `/api/v1/sync/state`, `/api/v1/search`).

---

## Act 4 — Tally on Lenovo laptop

The accounts machine runs Tally ERP 9 with XML Server on port **9000**.

### 4.1 Configure integration (admin desktop)

1. Settings → Tally
2. Enable integration
3. Host: `192.168.1.20` (Lenovo on LAN)
4. Company: **PRECISION LAPTOPS**
5. Sync interval: 300 seconds
6. Run **connection test** — stages: host resolution → TCP → XML

### 4.2 First synchronization

1. Admin triggers **Sync Now**
2. Server queues background sync
3. When Lenovo is online with Tally running, invoices import automatically
4. If workstation is offline, dashboard shows **waiting for workstation** (no crash)

---

## Act 5 — Data protection

### 5.1 Create backup

1. Admin → Backup → **Create full backup**
2. Validate integrity in UI
3. Copy `.webstudio-backup` file to NAS

### 5.2 Restore drill

1. Select backup → **Preview** restore scope
2. Run **settings-only** restore on staging clone (simulation used this scope)
3. Confirm emergency backup created before restore

---

## Act 6 — Verify operations

| Check | How |
|-------|-----|
| Reports | Inventory + Sales reports from desktop |
| AI | Product enrichment for new Lenovo SKU (Gemini in production; mock in test) |
| Images | Product image proxy serves authenticated requests |
| Auto startup | Reboot server → PostgreSQL → WEBSTUDIO service starts |
| Auto reconnect | Clients use discovery health; desktop retries on network blip |
| Business hours | `start-business-day.ps1` / `stop-business-day.ps1` for scripted open/close |

---

## Timeline (typical integrator)

| Day | Activity |
|-----|----------|
| Day 1 AM | Server + PostgreSQL + service |
| Day 1 PM | Setup + deployment wizard + desktop |
| Day 2 AM | Mobile devices + Tally config |
| Day 2 PM | Backup drill + staff training |
| Day 3 | Go-live with integrator on-site |

---

## Reference

- [CUSTOMER_INSTALLATION_CHECKLIST](../m12i/CUSTOMER_INSTALLATION_CHECKLIST.md)
- [DEPLOYMENT_CHECKLIST](../m12i/DEPLOYMENT_CHECKLIST.md)
- [TALLY_GUIDE](../m12h/TALLY_GUIDE.md)
