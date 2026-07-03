---
Title: First-Time Setup Master Guide — Two-PC LAN Deployment
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-03
Milestone: 14
Audience: Integrator, store IT, Main Admin
Related Documents:
  - docs/milestones/m14/README.md
  - docs/milestones/m14/INSTALLATION_MANUAL.md
  - docs/milestones/m12j/CUSTOMER_INSTALLATION_WALKTHROUGH.md
---

# First-Time Setup Master Guide

**Start here** for a new customer site with:

- **PC 1 — Dedicated server** (WEBSTUDIO Server + PostgreSQL)
- **PC 2 — Admin / staff desktop** (WEBSTUDIO Desktop)
- Optional: more desktops, Android/iOS phones, Tally billing laptop

This guide is the **ordered checklist**. Detailed steps live in the linked documents (already written in M12/M14).

---

## Topology (your two-PC test)

```
Office router (e.g. 192.168.1.1)
├── PC 1 — WEBSTUDIO Server     192.168.1.10  (static or DHCP reservation)
├── PC 2 — WEBSTUDIO Desktop    192.168.1.20  (DHCP OK)
├── Tally laptop (later)        192.168.1.30  (billing PC)
└── Phones (Wi‑Fi, same LAN)    DHCP
```

| Rule | Detail |
|------|--------|
| Desktop **never** talks to GitHub | Only to `http://<server-ip>:8000` |
| Server **may** talk to GitHub | Optional — for release sync only |
| PostgreSQL port 5432 | **localhost on server only** — never open to LAN |

---

## Complete document map

### Integrator / IT (install & network)

| Order | Document | Path |
|-------|----------|------|
| 1 | **This guide** | `docs/milestones/m14/FIRST_TIME_SETUP_MASTER_GUIDE.md` |
| 2 | Installation manual (14 steps) | `docs/milestones/m14/INSTALLATION_MANUAL.md` |
| 3 | First startup checklist | `docs/milestones/m14/FIRST_STARTUP_CHECKLIST.md` |
| 4 | Production commissioning | `docs/milestones/m14/PRODUCTION_COMMISSIONING_GUIDE.md` |
| 5 | Infrastructure checklist | `docs/milestones/m14/INFRASTRUCTURE_CHECKLIST.md` |
| 6 | Networking guide | `docs/milestones/m12h/NETWORKING_GUIDE.md` |
| 7 | Firewall guide | `docs/milestones/m14/FIREWALL_CONFIGURATION_GUIDE.md` |
| 8 | Server environment (.env) | `docs/milestones/m12a/PRODUCTION_ENVIRONMENT_CONFIGURATION.md` |
| 9 | Windows service | `docs/milestones/m12b/WINDOWS_SERVICE_GUIDE.md` |
| 10 | Installer / artifacts | `docs/milestones/m12c/INSTALLER_GUIDE.md` |
| 11 | Narrative walkthrough (fictional customer) | `docs/milestones/m12j/CUSTOMER_INSTALLATION_WALKTHROUGH.md` |

### Clients (desktop, mobile)

| Document | Path |
|----------|------|
| Desktop deployment | `docs/milestones/m14/DESKTOP_DEPLOYMENT_GUIDE.md` |
| Desktop user guide | `docs/milestones/m12h/DESKTOP_GUIDE.md` |
| Mobile deployment | `docs/milestones/m14/MOBILE_DEPLOYMENT_GUIDE.md` |
| Android guide | `docs/milestones/m12h/ANDROID_GUIDE.md` |
| iOS guide | `docs/milestones/m12h/IOS_GUIDE.md` |
| Client acceptance checklist | `docs/milestones/m14/CLIENT_ACCEPTANCE_CHECKLIST.md` |

### Tally

| Document | Path |
|----------|------|
| Tally production guide | `docs/milestones/m14/TALLY_PRODUCTION_GUIDE.md` |
| Tally validation checklist | `docs/milestones/m14/TALLY_VALIDATION_CHECKLIST.md` |
| XML verification | `docs/milestones/m14/XML_VERIFICATION_GUIDE.md` |
| Tally deployment (M12) | `docs/milestones/m12e/TALLY_DEPLOYMENT_GUIDE.md` |
| Tally operations | `docs/milestones/m12h/TALLY_GUIDE.md` |

### Updates, GitHub, operations

| Document | Path |
|----------|------|
| GitHub release sync | `docs/milestones/m13/GITHUB_RELEASE_SYNCHRONIZATION_REPORT.md` |
| Enterprise release CI | `docs/milestones/m13/CICD_PIPELINE_REPORT.md` |
| Operations manual (updates §3) | `docs/milestones/m14/OPERATIONS_MANUAL.md` |
| Operations handover | `docs/milestones/m14/OPERATIONS_HANDOVER.md` |
| Technical handover | `docs/milestones/m14/TECHNICAL_HANDOVER.md` |
| Administrator manual | `docs/milestones/m14/ADMINISTRATOR_MANUAL.md` |
| Backup manual | `docs/milestones/m14/BACKUP_MANUAL.md` |
| Disaster recovery | `docs/milestones/m14/DISASTER_RECOVERY_GUIDE.md` |

### End users (staff)

| Document | Path |
|----------|------|
| Quick start (15 min) | `docs/milestones/m14/QUICK_START_GUIDE.md` |
| User manual | `docs/milestones/m14/USER_MANUAL.md` |
| Training guide | `docs/milestones/m14/TRAINING_GUIDE.md` |
| FAQ | `docs/milestones/m14/FAQ.md` |
| Employee guide | `docs/milestones/m12h/EMPLOYEE_GUIDE.md` |

### Validation scripts (on server after install)

| Script | Path on server |
|--------|----------------|
| Firewall | `D:\WEBSTUDIO-IMS\infra\windows\configure-firewall.ps1` |
| Network validation | `D:\WEBSTUDIO-IMS\infra\windows\validate-production-network.ps1` |
| Full handover audit | `D:\WEBSTUDIO-IMS\infra\windows\validate-production-handover.ps1` |
| Tally validation | `D:\WEBSTUDIO-IMS\infra\windows\validate-production-tally.ps1` |
| Backup validation | `D:\WEBSTUDIO-IMS\infra\windows\validate-production-backup.ps1` |

---

## Phase 0 — Developer: publish release on GitHub

**When:** Before taking installers to the customer site.

1. Merge code → tag release, e.g. `v1.0.0`:
   ```bash
   git tag -a v1.0.0 -m "WEBSTUDIO IMS v1.0.0"
   git push origin v1.0.0
   ```
2. Wait for **GitHub Actions → Enterprise Release** to finish (quality gate + builds).
3. Download from **GitHub → Releases → v1.0.0**:
   - `WEBSTUDIO Server Setup.exe`
   - `WEBSTUDIO Desktop Setup.exe`
   - `WEBSTUDIO IMS.apk` (optional, for phones)
   - `checksums.sha256` — verify before copy to customer

**Reference:** `docs/milestones/m13/CICD_PIPELINE_REPORT.md`

> Initial testing does **not** require GitHub sync on the server — only the installer files.

---

## Phase 1 — Network planning (both PCs on same LAN)

**Reference:** `docs/milestones/m12h/NETWORKING_GUIDE.md`, `docs/milestones/m14/INFRASTRUCTURE_CHECKLIST.md`

### 1.1 Choose server IP

Pick a fixed address, e.g.:

| Setting | Example |
|---------|---------|
| Server IP | `192.168.1.10` |
| Subnet mask | `255.255.255.0` |
| Gateway | `192.168.1.1` (router) |
| DNS | `192.168.1.1` or `8.8.8.8` |

**Option A — DHCP reservation (recommended):** Reserve `192.168.1.10` for the server MAC address in the router admin UI.

**Option B — Static IP on server (Windows 11):**

1. **Settings → Network & Internet → Ethernet** (or Wi‑Fi if wired unavailable).
2. Click the adapter → **Edit** next to IP assignment → **Manual**.
3. IPv4 **On**:
   - IP address: `192.168.1.10`
   - Subnet mask: `255.255.255.0`
   - Gateway: `192.168.1.1`
   - DNS: `192.168.1.1`
4. Save. Document the IP on the handover sheet.

### 1.2 PC 2 (desktop)

DHCP is fine. It only needs to reach `http://192.168.1.10:8000`.

### 1.3 Wi‑Fi for phones

Use the **same LAN** as the server. Disable **AP/client isolation** on the router if phones cannot find the server.

### 1.4 Record for handover

| Field | Your site |
|-------|-----------|
| Server hostname | e.g. `WEBSTUDIO-SERVER` |
| Server IP | `192.168.1.10` |
| API URL | `http://192.168.1.10:8000` |
| Store subnet | e.g. `192.168.1.0/24` |

---

## Phase 2 — PC 1: Install WEBSTUDIO Server

**Reference:** `docs/milestones/m14/INSTALLATION_MANUAL.md` (steps 1–6)

1. Windows 11 Pro, updates, NTP/time zone correct.
2. Install **PostgreSQL 16** (or use bundled installer path).
3. Run **`WEBSTUDIO Server Setup.exe`** as Administrator.
4. Install root: `D:\WEBSTUDIO-IMS`.
5. Post-install creates `.env`, venv, runs migrations, registers service.

**Verify:**

```powershell
Get-Service "WEBSTUDIO Server"
Get-Service postgresql-x64-16
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

---

## Phase 3 — PC 1: Server `.env` configuration

**There is no full env GUI in the server EXE.** Edit the file:

`D:\WEBSTUDIO-IMS\config\env\.env`

Installer seeds from template and generates `JWT_SECRET`.

| Variable | Example / rule |
|----------|----------------|
| `APP_ENV` | `production` |
| `JWT_SECRET` | ≥32 chars (installer-generated) |
| `DATABASE_URL` | `postgresql+asyncpg://webstudio_app:PASSWORD@localhost:5432/webstudio` |
| `WEBSTUDIO_DATA_ROOT` | `D:\WEBSTUDIO-IMS` |
| `API_HOST` | `0.0.0.0` |
| `API_PORT` | `8000` |

After changes:

```powershell
Restart-Service "WEBSTUDIO Server"
```

**Reference:** `docs/milestones/m12a/PRODUCTION_ENVIRONMENT_CONFIGURATION.md`, INSTALLATION_MANUAL step 5.

---

## Phase 4 — PC 1: Firewall

**Reference:** `docs/milestones/m14/FIREWALL_CONFIGURATION_GUIDE.md`

Elevated PowerShell on **server**:

```powershell
cd D:\WEBSTUDIO-IMS\infra\windows
.\configure-firewall.ps1 -ApiPort 8000 -Subnet 192.168.1.0/24
.\validate-production-network.ps1 -ApiPort 8000
```

Opens:

- TCP **8000** inbound (API) from store subnet
- UDP **5353** inbound (mDNS discovery)
- Does **not** expose PostgreSQL 5432 to LAN

**From PC 2**, test:

```powershell
curl http://192.168.1.10:8000/health/live
```

---

## Phase 5 — PC 2: Install WEBSTUDIO Desktop

**Reference:** `docs/milestones/m14/DESKTOP_DEPLOYMENT_GUIDE.md`

1. Run **`WEBSTUDIO Desktop Setup.exe`** on the **second PC** (not necessarily the server).
2. Launch from Start Menu.
3. Connect to server:
   - Try auto-discovery (mDNS), or
   - **Manual URL:** `http://192.168.1.10:8000`
4. Allow Windows Firewall **outbound** to server if prompted.

**Pass:** Connection screen shows server / setup wizard appears.

---

## Phase 6 — First-time setup wizard (PC 2)

**Reference:** `docs/milestones/m14/FIRST_STARTUP_CHECKLIST.md` §6–7, `CUSTOMER_INSTALLATION_WALKTHROUGH.md` Act 2

1. App detects `system_initialized: false` → **Setup Wizard** (not login).
2. Enter company name, Main Admin username/password.
3. **Save recovery key** (shown once) — print and store securely.
4. Confirm recovery key.
5. Complete **Office Deployment Wizard** (detect network, backup paths, discovery URL).

**Verify:**

```http
GET http://192.168.1.10:8000/api/v1/setup/status
→ system_initialized: true
```

Log in as Main Admin.

---

## Phase 7 — Additional staff desktops / laptops

**Reference:** `docs/milestones/m14/DESKTOP_DEPLOYMENT_GUIDE.md`, `CLIENT_ACCEPTANCE_CHECKLIST.md`

For each extra Windows/Mac PC on the LAN:

1. Install `WEBSTUDIO Desktop Setup.exe` (or DMG on Mac).
2. Manual server URL: `http://192.168.1.10:8000` (or mDNS if same subnet).
3. Log in with user accounts created by Main Admin.
4. Confirm role-based menus (Sales vs Admin).

No per-PC GitHub or `.env` configuration.

---

## Phase 8 — Mobile phones (Android / iOS)

**Reference:** `docs/milestones/m14/MOBILE_DEPLOYMENT_GUIDE.md`

### Android

1. Copy `WEBSTUDIO IMS.apk` from GitHub Release (or server Deployment Center later).
2. Enable “Install unknown apps” if sideloading.
3. Install APK.
4. First launch → server URL: `http://192.168.1.10:8000`.
5. Log in.

### iOS

1. Install via TestFlight / App Store path per your distribution plan.
2. Server URL same as above.
3. Updates are **notification + App Store** — no direct IPA from server.

**Network:** Phone must be on Wi‑Fi that routes to `192.168.1.10:8000`.

---

## Phase 9 — Tally ERP 9 (billing laptop)

**Reference:** `docs/milestones/m14/TALLY_PRODUCTION_GUIDE.md`

Typical layout:

- Tally on a **separate billing laptop** (not the WEBSTUDIO server).
- Tally XML port **9000** on billing PC.
- WEBSTUDIO Server connects **outbound** to Tally.

Steps:

1. Install Tally ERP 9 on billing PC; enable XML on port 9000.
2. On **desktop (Main Admin)** → **Settings → Tally**:
   - Enable integration
   - Host: billing PC IP (e.g. `192.168.1.30`)
   - Port: `9000`
   - Company name as in Tally
3. Run **Test connection** in Settings.
4. Validate: `infra/windows/validate-production-tally.ps1` on server.

Until Tally is configured, inventory/sales still work; sync stays offline.

---

## Phase 10 — Enable auto-update chain (after basic testing works)

Auto-update is **three hops** — none are fully automatic end-to-end:

```
GitHub Release → Server downloads → Admin approves Deploy → Desktops prompted
```

### 10.1 One-time GitHub config (server `.env` only)

Add to `D:\WEBSTUDIO-IMS\config\env\.env`:

```env
WEBSTUDIO_GITHUB_REPO=Smarthsingh/WEBSTUDIO-IMS
WEBSTUDIO_GITHUB_TOKEN=ghp_xxxxxxxx
WEBSTUDIO_RELEASE_SYNC_INTERVAL_SECONDS=900
WEBSTUDIO_RELEASE_UPDATES_ROOT=D:\WEBSTUDIO-IMS\Updates
WEBSTUDIO_RELEASE_SYNC_SCHEDULER=1
```

Create PAT on GitHub with **read access to repo/releases** (private repo).

Restart **WEBSTUDIO Server** service.

### 10.2 Enable in application settings

Main Admin → **Settings** (system setting):

- `github_release_sync_enabled` = **true**
- `github_release_repo` = `Smarthsingh/WEBSTUDIO-IMS` (if not using env only)

### 10.3 Each new release (your workflow)

1. You push tag `v1.0.1` → CI publishes GitHub Release.
2. Server polls (~15 min) or **Deployment Center → Check updates**.
3. Main Admin: **Backup** → **Validate** → **Deploy** (approval checkbox).
4. Staff desktops: app checks server every ~6h → update dialog → install from server.

**References:**

- `docs/milestones/m13/GITHUB_RELEASE_SYNCHRONIZATION_REPORT.md`
- `docs/milestones/m14/OPERATIONS_MANUAL.md` §3 Updates
- `docs/database/github-release-sync.md`

Desktop **never** needs GitHub URL or token.

---

## Phase 11 — Post-setup validation

Run on server (elevated PowerShell):

```powershell
cd D:\WEBSTUDIO-IMS\infra\windows
.\validate-production-network.ps1 -ApiPort 8000
.\validate-production-backup.ps1
.\validate-production-handover.ps1   # needs Main Admin JWT — see script help
```

Or from desktop (logged in as Network Admin):

```http
GET /api/v1/deployment/production-handover
GET /api/v1/deployment/client-validation
```

**Checklists:**

- `docs/milestones/m14/CLIENT_ACCEPTANCE_CHECKLIST.md`
- `docs/milestones/m14/USER_ACCEPTANCE_CHECKLIST.md`
- `docs/milestones/m14/FIRST_STARTUP_CHECKLIST.md`

---

## Phase 12 — Handover to daily operations

| Role | Read |
|------|------|
| Main Admin | `ADMINISTRATOR_MANUAL.md`, `OPERATIONS_MANUAL.md` |
| IT | `MAINTENANCE_GUIDE.md`, `OPERATIONS_HANDOVER.md` |
| Staff | `QUICK_START_GUIDE.md`, `USER_MANUAL.md` |

---

## Quick troubleshooting (two-PC setup)

| Symptom | Check |
|---------|--------|
| Desktop cannot find server | Manual URL `http://<server-ip>:8000`; firewall §4; same subnet |
| `health/ready` fails | PostgreSQL running; `DATABASE_URL`; migrations |
| Login blocked | Complete setup wizard first (`/api/v1/setup/status`) |
| Phone offline | Wi‑Fi isolation; use server IP not `localhost` on phone |
| Tally sync failed | Tally XML on; billing PC IP; firewall on billing PC for port 9000 |
| Updates not appearing | GitHub sync enabled; Deployment Center approve deploy; server upgraded first |

**Reference:** `docs/milestones/m12h/TROUBLESHOOTING_GUIDE.md`, `docs/milestones/m14/FAQ.md`

---

## Summary: what is manual vs automatic

| Step | Automatic? |
|------|------------|
| CI build on git tag | Yes |
| Server downloads from GitHub | Yes (if sync enabled) |
| Server deploy new version | **No** — admin approves |
| Desktop install update | **Prompt** — user clicks install |
| Tally import | Yes (scheduler) when configured |
| `.env` / secrets | **Manual** file edit on server |
| Static IP | **Manual** (router or Windows) |
| Setup wizard | **Once**, manual on first desktop |

---

*Milestone index: [docs/milestones/m14/README.md](README.md)*
