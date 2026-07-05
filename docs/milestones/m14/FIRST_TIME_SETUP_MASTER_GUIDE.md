---
Title: WEBSTUDIO IMS — Complete Customer Office Setup Guide
Version: 3.2.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-03
Milestone: 14
Release: v1.0.2+
Site: Customer showroom (Jio + Tenda two-floor LAN)
Audience: Store owner, integrator, Main Admin
Related Documents:
  - docs/milestones/m14/INSTALLATION_MANUAL.md
  - docs/milestones/m14/OPERATIONS_MANUAL.md
  - docs/milestones/m14/TALLY_PRODUCTION_GUIDE.md
---

# WEBSTUDIO IMS — Complete Office Setup Guide

**Read this document top to bottom.** It is written for **your shop** with real network names, IPs, firewall commands, and install steps.

---

## Site handover sheet (print this)

```text
═══════════════════════════════════════════════════════════
WEBSTUDIO IMS — YOUR SHOP (PRODUCTION)
═══════════════════════════════════════════════════════════
Server URL (all apps):     http://192.168.29.100:8000
Gateway (Jio router):      192.168.29.1
Subnet:                    192.168.29.0 / 255.255.255.0

1st floor Wi‑Fi:           JioBharat
Ground floor Wi‑Fi:        Asus Store  (Tenda AP mode)

WEBSTUDIO Server PC:
  Computer name:           WEBSTUDIO-SERVER
  Wi‑Fi:                   JioBharat
  Fixed IP:                192.168.29.100
  MAC (for Jio reservation): E0:AD:47:31:CA:0A

Tally laptop:
  Computer name:           TALLY-LAPTOP
  IP:                      DHCP (changes — do NOT use IP in settings)
  Example IP now:          192.168.29.176
  Tally XML port:          9000

Installers from GitHub:
  https://github.com/Smarthsingh/WEBSTUDIO-IMS/releases → v1.0.1

Release notes (v1.0.1 — CI verified):
  - All release assets built successfully (Server, Desktop, APK)
  - Server installer bundles Python + NSSM (no manual Python install)
  - Desktop: WEBSTUDIO brand icon, logos on login, no File/Edit menu
  - PostgreSQL 16/17/18 auto-detected (your site: postgresql-x64-18)

Main Admin username:       _______________________
Recovery key stored at:    _______________________
Install date:              _______________________
═══════════════════════════════════════════════════════════
```

---

## Your network layout

```
                         INTERNET
                             │
                    ┌────────▼────────┐
                    │   Jio Router    │  192.168.29.1
                    │  Wi‑Fi: JioBharat│  (1st floor main)
                    └────────┬────────┘
                             │ LAN cable
              ┌──────────────┼──────────────┐
              │              │              │
    ┌─────────▼─────────┐    │    ┌─────────▼─────────┐
    │ WEBSTUDIO Server  │    │    │  Tenda (AP mode)  │
    │ WEBSTUDIO-SERVER  │    │    │  Wi‑Fi: Asus Store │
    │ 192.168.29.100    │    │    │  (ground floor)   │
    │ Wi‑Fi: JioBharat  │    │    └─────────┬─────────┘
    └───────────────────┘    │              │
              │              │    ┌─────────▼─────────┐
    ┌─────────▼─────────┐    │    │ Staff laptops &   │
    │ TALLY-LAPTOP      │    │    │ phones (GF)       │
    │ DHCP (.176 etc.)  │    │    │ DHCP automatic    │
    │ moves 1F ↔ GF     │    │    └───────────────────┘
    └───────────────────┘    │
              │              │
    Staff laptops / phones (1st floor, JioBharat, DHCP)
```

| Rule | Detail |
|------|--------|
| All devices use **local** IPs `192.168.29.x` | Not public IP `49.43.x.x` |
| Server URL for **every** app | `http://192.168.29.100:8000` |
| Staff laptops & phones | **DHCP only** — no static IP |
| Tally laptop | **DHCP** + hostname **`TALLY-LAPTOP`** in WEBSTUDIO |
| PostgreSQL port 5432 | **Server localhost only** — never open to LAN |

---

## IPs you must NOT use (already taken)

| IP / range | Used by |
|------------|---------|
| `192.168.29.10` | Fixed device / camera (MAC `bc:ad:28:9a:ad:a4`) |
| `192.168.29.50` – `192.168.29.67` | CCTV cameras (block on Jio router) |
| `192.168.29.4`, `.9`, etc. | Other fixed LAN devices |

**WEBSTUDIO Server is assigned:** `192.168.29.100` (outside camera range).

---

## Public IP vs local IP (do not confuse)

| What you see | Example | Use for WEBSTUDIO? |
|--------------|---------|-------------------|
| Google “what is my IP” | `49.43.133.113` | **No** — internet only |
| Phone/laptop Wi‑Fi details | `192.168.29.x` | **Yes** |
| Server | `192.168.29.100` | **Yes — this is the app URL host** |

---

# PART 0 — Download installers from GitHub

1. Open: **https://github.com/Smarthsingh/WEBSTUDIO-IMS/releases**
2. Click release **`v1.0.2`** (or latest)
3. Under **Assets**, download:

| File | Install on |
|------|------------|
| **`WEBSTUDIO Server Setup.exe`** | Server PC (`WEBSTUDIO-SERVER`) |
| **`WEBSTUDIO Desktop Setup.exe`** | Every staff laptop |
| **`WEBSTUDIO IMS.apk`** | Android phones |
| **`checksums.sha256`** | Optional verify |

If Releases is empty, check **Actions → Enterprise Release** finished green, then refresh Releases.

> **Release v1.0.2 — server install fixes:** Post-install prompts for DB password, runs Alembic correctly, HTTP-only (no TLS crash), NSSM gets full `.env`. Use **`finalize-server-setup.ps1`** if recovering an older install.

> **Do not use v1.0.0 / v1.0.1 server builds** for fresh installs — use v1.0.2+ or run `finalize-server-setup.ps1` after v1.0.1.

---

# PART 0B — What must be preinstalled (before setup)

## Server PC (`WEBSTUDIO-SERVER`) — required

| Software | Your site | Notes |
|----------|-----------|--------|
| **Windows 11 Pro** | Required | Updated, Administrator access |
| **PostgreSQL 16+** | **PostgreSQL 18** (`postgresql-x64-18`) | Install from [postgresql.org](https://www.postgresql.org/download/windows/) — service must be **Running** |
| **Database + user** | Create **before** Server Setup | See **Part C2** |

## Server PC — NOT required (bundled in v1.0.1 installer)

| Do NOT install separately | Why |
|-----------------------------|-----|
| Python 3.12 / 3.14 | Bundled at `D:\WEBSTUDIO-IMS\runtime\python\` |
| NSSM | Bundled at `D:\WEBSTUDIO-IMS\tools\nssm\` |
| Manual `pip install` | Post-install runs automatically |
| Node.js / pnpm | Server only — not needed on server |

## Staff laptops — required

| Software | Notes |
|----------|--------|
| **Windows 10/11** | 64-bit |
| **WEBSTUDIO Desktop Setup.exe** (v1.0.1) | From GitHub Releases only |

## Staff laptops — NOT required

| Do NOT install | Why |
|----------------|-----|
| Python, PostgreSQL, Node | Desktop talks to server over HTTP |
| Git / repo clone | Not needed on staff PCs |

## Phones — required

| Software | Notes |
|----------|--------|
| **Android** | APK sideload from Releases |

## Tally laptop — required (Part G)

| Software | Notes |
|----------|--------|
| **Tally ERP 9** | XML port **9000** enabled |
| Computer name **`TALLY-LAPTOP`** | Used in WEBSTUDIO settings (not IP) |

---

# PART 0C — Clean install (if old setup failed)

If you previously ran **v1.0.0** Server Setup or have a broken `D:\WEBSTUDIO-IMS` folder, remove it **before** v1.0.1.

### Server PC — remove old WEBSTUDIO

**PowerShell as Administrator:**

```powershell
# Stop/remove service if it exists
powershell -ExecutionPolicy Bypass -File "D:\WEBSTUDIO-IMS\infra\windows\uninstall-webstudio-service.ps1" -InstallRoot "D:\WEBSTUDIO-IMS" -ErrorAction SilentlyContinue

# Or via Settings → Apps → Uninstall WEBSTUDIO Server

# Delete install folder
Remove-Item -Recurse -Force "D:\WEBSTUDIO-IMS" -ErrorAction SilentlyContinue
```

**Keep PostgreSQL 18** — do not uninstall PostgreSQL unless you intend to recreate the database.

To wipe database and start fresh (optional):

```sql
-- pgAdmin / psql as postgres superuser
DROP DATABASE IF EXISTS webstudio;
-- Then recreate in Part C2
```

### Staff laptops — remove old Desktop

**Settings → Apps → WEBSTUDIO Desktop → Uninstall**

Then install **`WEBSTUDIO Desktop Setup.exe`** from **v1.0.1**.

### Smart App Control (unsigned desktop EXE)

If Windows blocks the desktop installer:

1. Right-click EXE → **Properties** → **Unblock** → OK  
2. Or **More info** → **Run anyway** on first launch  

Code signing can be added later via GitHub secrets (`WIN_CSC_LINK`).

---

# PART A — NETWORK SETUP

## A1 — Confirm Tenda is AP mode (ground floor)

You already confirmed **Tenda → AP mode** at `tendawifi.com`. Keep:

| Setting | Value |
|---------|--------|
| Working mode | **AP** |
| DHCP on Tenda | **Off** (Jio assigns all IPs) |
| AP / wireless isolation | **Off** |
| Cable | Jio **LAN** → Tenda **LAN** (not WAN) |

Opening `http://192.168.29.1` from ground floor showing **Jio admin** is **correct** — one shared network.

## A2 — Jio router checks

Log into **`http://192.168.29.1`**:

| Setting | Action |
|---------|--------|
| AP / client isolation (JioBharat) | **Off** |
| Guest Wi‑Fi | Staff must **not** use for WEBSTUDIO |

## A3 — Reserve server IP on Jio (recommended)

**Settings → DHCP / Address reservation** (name varies):

| Field | Value |
|-------|--------|
| MAC address | `E0:AD:47:31:CA:0A` |
| Reserved IP | `192.168.29.100` |
| Name | `WEBSTUDIO-SERVER` |

Save → on server PC: disconnect/reconnect **JioBharat** Wi‑Fi or reboot.

Verify on server:

```text
ipconfig
```

Under **Wireless LAN adapter Wi‑Fi**:

```text
IPv4 Address. . . . . . . . . . . : 192.168.29.100
Default Gateway . . . . . . . . . : 192.168.29.1
```

> **Note:** `ipconfig /release` may show *"Ethernet 2 media disconnected"* — ignore it. That is an unplugged wired port. Only check **Wi‑Fi** section.

### Alternative — manual static IP on server Wi‑Fi

**Settings → Network & Internet → Wi‑Fi → JioBharat → Properties → IP assignment → Manual:**

| Field | Value |
|-------|--------|
| IP address | `192.168.29.100` |
| Subnet mask | `255.255.255.0` |
| Gateway | `192.168.29.1` |
| DNS | `192.168.29.1` |

## A4 — Server PC network profile

**Wi‑Fi JioBharat → Network profile → Private** (not Public).

## A5 — Staff laptops and phones

| Device | IP setup | Firewall |
|--------|----------|----------|
| All staff laptops | **Automatic (DHCP)** | No ping rules needed |
| All phones | **Automatic (DHCP)** | N/A |
| TALLY-LAPTOP | **Automatic (DHCP)** | Allow Tally port 9000 (see Part G) |

On **each** staff laptop: Wi‑Fi → **Private**. When WEBSTUDIO Desktop asks → **Allow on private networks**.

## A6 — Network tests before install

### Test 1 — Same LAN on both floors

| Location | Wi‑Fi | `ipconfig` IPv4 | Gateway |
|----------|-------|-----------------|---------|
| 1st floor laptop | JioBharat | `192.168.29.x` | `192.168.29.1` |
| Ground floor laptop | Asus Store | `192.168.29.x` | `192.168.29.1` |

Gateways must **match**.

### Test 2 — Reach server (after IP is `.100`)

From **ground floor** laptop browser:

```text
http://192.168.29.100:8000/health/live
```

(Works after WEBSTUDIO Server installed; before install = connection refused is normal.)

### Test 3 — Ping (optional)

Ping between PCs often fails on Windows even when WEBSTUDIO works. If you need ping for testing, on **server only**:

```powershell
New-NetFirewallRule -DisplayName "WEBSTUDIO Test Ping In" -Protocol ICMPv4 -IcmpType 8 -Direction Inbound -Action Allow -Profile Private
```

Remove later (not required for production):

```powershell
Remove-NetFirewallRule -DisplayName "WEBSTUDIO Test Ping In"
```

---

# PART B — WINDOWS FIREWALL ON SERVER PC

Run **PowerShell as Administrator** on **WEBSTUDIO-SERVER**.

## B1 — WEBSTUDIO API rules (required after server install)

```powershell
cd D:\WEBSTUDIO-IMS\infra\windows
.\configure-firewall.ps1 -ApiPort 8000 -Subnet 192.168.29.0/24
```

Creates:

| Rule | Port | Purpose |
|------|------|---------|
| WEBSTUDIO IMS API Inbound | TCP **8000** | Desktop + mobile apps |
| WEBSTUDIO IMS mDNS | UDP **5353** | Auto-discovery on LAN |

## B2 — Before install (if testing port early)

If server is not installed yet but you want to test firewall:

```powershell
New-NetFirewallRule -DisplayName "WEBSTUDIO API In" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000 -Profile Private -RemoteAddress 192.168.29.0/24
New-NetFirewallRule -DisplayName "WEBSTUDIO mDNS" -Direction Inbound -Action Allow -Protocol UDP -LocalPort 5353 -Profile Private -RemoteAddress 192.168.29.0/24
```

## B3 — Verify firewall rules

```powershell
Get-NetFirewallRule -DisplayName "WEBSTUDIO IMS*" | Format-Table DisplayName, Enabled, Direction, Action
```

## B4 — What NOT to open on server

| Port | Action |
|------|--------|
| **5432** (PostgreSQL) | **Never** open to LAN |
| **9000** (Tally) | **Outbound** from server to TALLY-LAPTOP — no inbound rule on server |

## B5 — Staff laptops

**No inbound firewall rules needed.** Outbound to `192.168.29.100:8000` is allowed by default.

---

# PART C — INSTALL WEBSTUDIO SERVER

On **WEBSTUDIO-SERVER** (`192.168.29.100`, Wi‑Fi **JioBharat**).

## C0 — Prerequisites checklist

Before running **`WEBSTUDIO Server Setup.exe`**:

| # | Check | Command / action |
|---|--------|------------------|
| 1 | Windows 11 Pro, name `WEBSTUDIO-SERVER` | Settings → System → About |
| 2 | IP **`192.168.29.100`** on Wi‑Fi | `ipconfig` |
| 3 | Wi‑Fi profile **Private** | Settings → Wi‑Fi → JioBharat |
| 4 | **PostgreSQL running** | `Get-Service postgresql-x64-18` → Running |
| 5 | Database **`webstudio`** + user **`webstudio_app`** created | pgAdmin (**Part C2**) |
| 6 | Old `D:\WEBSTUDIO-IMS` removed (if retrying) | Part 0C |
| 7 | Installer downloaded | **v1.0.1** `WEBSTUDIO Server Setup.exe` |

**You do NOT need:** Python, NSSM, or manual venv — v1.0.1 installer includes them.

## C1 — Prepare Windows

1. Windows 11 Pro, updated.
2. Computer name: **`WEBSTUDIO-SERVER`**
3. Confirm IP: **`192.168.29.100`** (`ipconfig`)
4. Wi‑Fi profile: **Private**

## C2 — Create PostgreSQL database (required before installer)

Your PostgreSQL service: **`postgresql-x64-18`** (PostgreSQL 18).

**pgAdmin** or **psql** as `postgres` superuser:

```sql
CREATE USER webstudio_app WITH LOGIN PASSWORD 'YourStrongPassword123!';
CREATE DATABASE webstudio OWNER webstudio_app;
GRANT ALL PRIVILEGES ON DATABASE webstudio TO webstudio_app;
```

In pgAdmin: when creating the role, ensure **Can login?** is **checked**.

Write down the password — you will need it in `.env` if the installer does not set it correctly.

## C3 — Run installer

1. Copy **`WEBSTUDIO Server Setup.exe`** (v1.0.2 or later) to the server
2. **Right-click → Run as administrator**
3. Install path: **`D:\WEBSTUDIO-IMS`**
4. Wait for **post-install** (PowerShell window stays open):
   - Bundled Python + NSSM
   - **Prompts for `webstudio_app` password** (same as pgAdmin Part C2)
   - Runs Alembic migrations automatically
   - Registers and starts **WEBSTUDIO Server** service
5. Post-install log: **`D:\WEBSTUDIO-IMS\logs\install-post.log`**

> **v1.0.2+ fixes:** correct Alembic path, HTTP-only (no missing TLS certs), `.env` synced to backend, NSSM gets full environment.

### If post-install could not prompt (unattended / closed early)

Run **once** as Administrator:

```powershell
powershell -ExecutionPolicy Bypass -File "D:\WEBSTUDIO-IMS\infra\windows\finalize-server-setup.ps1"
```

Enter `webstudio_app` password when asked. See **Part J1** only if this fails.

## C4 — Verify services

```powershell
Get-Service postgresql-x64-18
Get-Service "WEBSTUDIO Server"
curl.exe http://127.0.0.1:8000/health/live
curl.exe http://127.0.0.1:8000/health/ready
```

Expected:

- PostgreSQL: **Running**
- WEBSTUDIO Server: **Running**
- `/health/live` and `/health/ready`: **200 OK**

Optional bundled runtime check:

```powershell
Test-Path "D:\WEBSTUDIO-IMS\runtime\python\python.exe"   # True
Test-Path "D:\WEBSTUDIO-IMS\tools\nssm\nssm.exe"         # True
Test-Path "D:\WEBSTUDIO-IMS\config\env\.env"             # True
```

## C5 — Confirm `.env` (usually automatic)

File: **`D:\WEBSTUDIO-IMS\config\env\.env`**

Installer + post-install should already set:

```env
APP_ENV=production
API_HOST=0.0.0.0
API_PORT=8000
WEBSTUDIO_DATA_ROOT=D:\WEBSTUDIO-IMS
WEBSTUDIO_DISCOVERY_CANDIDATES=192.168.29.100,WEBSTUDIO-SERVER
DATABASE_URL=postgresql+asyncpg://webstudio_app:YOUR_PASSWORD@127.0.0.1:5432/webstudio
JWT_SECRET=(auto-generated, 32+ chars)
TLS_CERT_PATH=
TLS_KEY_PATH=
```

**Use `webstudio_app` password — not the postgres superuser password.**

`TLS_CERT_PATH` and `TLS_KEY_PATH` must stay **empty** for HTTP on port **8000** (shop LAN). Do not point to missing cert files.

If you change `.env` later:

```powershell
powershell -ExecutionPolicy Bypass -File "D:\WEBSTUDIO-IMS\infra\windows\finalize-server-setup.ps1"
```

## C6 — Run firewall script

```powershell
powershell -ExecutionPolicy Bypass -File "D:\WEBSTUDIO-IMS\infra\windows\configure-firewall.ps1" -ApiPort 8000 -Subnet 192.168.29.0/24
powershell -ExecutionPolicy Bypass -File "D:\WEBSTUDIO-IMS\infra\windows\validate-production-network.ps1" -ApiPort 8000
```

## C7 — Test from ground floor

On laptop connected to **Asus Store**, browser:

```text
http://192.168.29.100:8000/health/live
```

Must return OK. If yes → both floors reach server.

---

# PART D — FIRST DESKTOP + SETUP WIZARD

On any admin laptop (1st or ground floor).

> **Install server first** — desktop shows "Connecting to server" until `http://192.168.29.100:8000/health/live` works in a browser.

## D1 — Install desktop (v1.0.1)

1. Uninstall old **WEBSTUDIO Desktop** if present (Settings → Apps)
2. Run **`WEBSTUDIO Desktop Setup.exe`** from **v1.0.1**
3. If Smart App Control blocks: **Unblock** in Properties or **Run anyway**
4. Launch from Start Menu — icon should show **WEBSTUDIO** brand mark
5. App window has **no File/Edit/View menu bar** (normal for v1.0.1)

Login screen shows **outlet addresses** and **brand logos** on the left panel.

## D2 — Connect

Manual server URL:

```text
http://192.168.29.100:8000
```

Allow Windows Firewall if prompted (**Private**).

## D3 — Setup Wizard (one time)

| Step | Action |
|------|--------|
| 1 | Company name |
| 2 | Main Admin username + password |
| 3 | **Recovery key** — print and store safely |
| 4 | Confirm recovery key |
| 5 | Office Deployment Wizard — confirm server URL and backup path |

## D4 — Verify

Browser (any PC):

```text
http://192.168.29.100:8000/api/v1/setup/status
```

→ `"system_initialized": true`

Log in as Main Admin.

---

# PART E — ALL STAFF LAPTOPS (both floors)

Repeat on every staff PC. Examples from your network (IPs change with DHCP — only server URL is fixed):

| PC name | Typical IP (DHCP) | Wi‑Fi |
|---------|-------------------|-------|
| DESKTOP-KCJR6LL | e.g. `.22` | Asus Store or JioBharat |
| LAPTOP-8JSTAM1P | e.g. `.24` | Either |
| DESKTOP-AIKQ3P8 | e.g. `.76` | Either |
| LAPTOP-FP4H6675 | e.g. `.246` | Either |
| Others | automatic | Either |

**Every laptop:**

1. Uninstall old desktop app if present
2. Install **`WEBSTUDIO Desktop Setup.exe`** (**v1.0.1**)
3. Server URL: **`http://192.168.29.100:8000`**
4. Wi‑Fi → **Private**
5. Log in with user account (Main Admin creates users in **Settings → Users**)

**No static IP. No GitHub token. No `.env` on laptops.**

---

# PART F — PHONES (Android)

| Phone (examples) | DHCP IP (changes) |
|------------------|-------------------|
| Smarth-s-S22 | e.g. `.233` |
| Galaxy-M14 | e.g. `.87` |

## F1 — Install APK

1. Copy **`WEBSTUDIO IMS.apk`** to the phone
2. Install (allow **unknown apps** if Android asks)
3. Join shop Wi‑Fi (**JioBharat** or **Asus Store** — same network as server)

## F2 — First launch (connect to server)

> **Do not use `10.0.2.2`** — that address is for Android **emulator only**. On a real phone it will hang or fail.

1. Open **WEBSTUDIO IMS**
2. App opens **Connect to Server** and starts **automatic discovery** (mDNS + LAN scan for `192.168.29.100`)
3. If the server is found on the LAN → app **connects automatically**
4. **While searching**, the **Server address** field is already visible — you can enter manually at any time:

```text
http://192.168.29.100:8000
```

5. Tap **Connect to server** (works even during network scan)
6. If discovery fails → field is pre-filled with the shop server URL — confirm and tap **Connect to server**
7. **Settings → API server** (after login) returns here to change server later
8. When connected → log in with staff credentials

## F3 — Barcode scanning (inventory)

1. Open **Inventory** (or **Stock** browse)
2. Tap the **scan** icon in the toolbar (or **Barcode scan** in lookup sheets / Add Laptop wizard)
3. Allow **Camera** when Android asks (required once)
4. Point at the **manufacturer barcode** on the laptop box (Code 128, EAN, UPC, etc.)
5. App detects **serial number**, **model number**, or **part number** automatically

> **Note:** Phone scans **manufacturer barcodes** on product boxes — not desktop inventory QR codes.

If camera fails: **Android Settings → Apps → WEBSTUDIO IMS → Permissions → Camera → Allow**, then tap **Retry camera** in the scanner.

## F4 — Troubleshooting mobile connection

| Symptom | Fix |
|---------|-----|
| Stuck on splash showing `10.0.2.2:8000` | Reinstall **v1.0.2+** APK; then enter `http://192.168.29.100:8000` manually |
| “Server not found” | Phone on same Wi‑Fi as server; test `http://192.168.29.100:8000/health/live` in phone browser |
| Works on desktop, not phone | Server firewall done; phone not on guest/isolated Wi‑Fi |
| Connection saved but fails later | **Settings → API server** → re-enter `http://192.168.29.100:8000` |

**Server URL for every phone:** **`http://192.168.29.100:8000`** (fixed — not the phone’s own IP).

## F5 — Rebuild APK with server URL baked in (optional, IT)

When building the release APK, embed the shop server URL so staff never type it:

```bash
flutter build apk --release \
  --dart-define=WEBSTUDIO_DEFAULT_API_URL=http://192.168.29.100:8000
```

Or use `pnpm release:android` after setting that define in the release script.

---

# PART G — TALLY-LAPTOP (moves 1st floor ↔ ground floor)

## G1 — Your Tally machine

| Field | Value |
|-------|--------|
| Computer name | **`TALLY-LAPTOP`** (you set this) |
| Current IP (example) | `192.168.29.176` — **will change** when switching Wi‑Fi |
| Gateway | `192.168.29.1` |
| Wi‑Fi | JioBharat or Asus Store |

**Never enter `192.168.29.176` in WEBSTUDIO** — use hostname instead (enter it in **Settings → Tally → Tally workstation address**; see Part **G4**).

## G2 — Tally ERP 9 on TALLY-LAPTOP

1. Install Tally ERP 9
2. With **company open** (not just the gateway screen), press **F12** → **Advanced Configuration**
3. Set:

| Setting | Value |
|---------|--------|
| Tally acting as | **Both** or **Server** |
| Enable ODBC / XML | **Yes** |
| Port | **9000** |

4. **Quit Tally completely** (system tray too) → reopen → open company
5. **Verify XML is listening** (PowerShell on TALLY-LAPTOP):

```powershell
netstat -an | findstr 9000
Test-NetConnection localhost -Port 9000
```

Expected: `TCP 0.0.0.0:9000 ... LISTENING` and `TcpTestSucceeded : True`

If **no output** from `netstat` → XML is not running; recheck F12 settings or edit `tally.ini` (`EnableODBCServer=Yes`, port `9000`), then restart Tally.

6. Note exact **company name** as shown in Tally (for WEBSTUDIO Settings → Tally)

## G3 — Firewall on TALLY-LAPTOP

**PowerShell as Administrator** on TALLY-LAPTOP:

```powershell
New-NetFirewallRule -DisplayName "Tally XML 9000" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 9000 -Profile Private
```

Wi‑Fi on both floors → **Private**.

## G4 — Connect Tally in WEBSTUDIO (Main Admin desktop)

Open the desktop app on any admin PC → **Settings** → **Tally** (Connection settings screen).

> **Important:** The app does **not** have a separate field labeled “laptop name.” You enter the Tally PC’s **Windows computer name** in **Tally workstation address** (hostname or IP). The hint under that field says: *“Hostname or IP of the PC running Tally with XML Server enabled.”*

### G4.1 — Find the Tally laptop name

On **TALLY-LAPTOP**, open **PowerShell** or **Command Prompt**:

```powershell
hostname
```

Example output: `TALLY-LAPTOP`. Use that exact value in WEBSTUDIO (unless you chose a different computer name in Windows).

To set or check the name: **Settings → System → About → Rename this PC**.

### G4.2 — Map each screen field to your shop values

| What you see in WEBSTUDIO | What to enter | Notes |
|---------------------------|---------------|--------|
| **Enable automatic Tally synchronization** | ☑ Checked | Turn on when Tally XML and firewall on TALLY-LAPTOP are ready |
| **Tally workstation address** | **`TALLY-LAPTOP`** | This is the **laptop name** (hostname). **Do not** leave `127.0.0.1` — that only works if Tally runs on the **same PC as the server**, which is not your layout |
| **Port** | **`9000`** | Default Tally XML port |
| **Company name in Tally** | Exact name from Tally | **Copy from Tally’s company list** — on Tally Prime this is often **not** just `WEBSTUDIO`. Example: `WEBSTUDIO - (from 1-Apr-2022) - (from 1-Apr-25) - (from 1-Apr-26)`. Wrong name → sync shows Success with **0 checked / 0 imported** |
| **Polling interval** | **`300`** (or default) | How often IMS checks Tally for new invoices (seconds) |

### G4.3 — Save and test

1. Click **Save** (or save the form if prompted).
2. Click **Test connection**.
3. Expected: success message when TALLY-LAPTOP is on the same shop Wi‑Fi (JioBharat or Asus Store), Tally is open with that company, and port **9000** is allowed in firewall (Part G3).

### G4.4 — Common mistakes

| Mistake | Fix |
|---------|-----|
| Left **Tally workstation address** as `127.0.0.1` | Use **`TALLY-LAPTOP`** (output of `hostname` on the Tally PC) |
| Used Tally laptop IP (e.g. `192.168.29.176`) | Prefer **hostname** so sync still works when the laptop moves floors and gets a new IP |
| **Company name in Tally** does not match Tally | Copy the **full** name from Tally (Gateway → company list, or `List of Companies` XML test on server). Tally Prime often appends `(from 1-Apr-…)` suffixes |
| Test fails after moving to ground floor | TALLY-LAPTOP Wi‑Fi → **Private**; Tenda **AP isolation Off**; Tally XML still on port 9000 |
| Forgot firewall on TALLY-LAPTOP | Run Part **G3** rule on the **Tally laptop**, not the server |
| **`netstat` shows no port 9000** | Tally XML off — repeat **G2** (full restart + company open) |
| Tally sync **Success** but **0 checked / 0 imported** | (1) **Company name** wrong — use full Tally Prime name (see G4). (2) Tally stuck on **Import/GSTR** screen — press Esc to Gateway. (3) Server on **v1.0.1** — upgrade to **v1.0.2+** (Day Book export for Tally Prime) |

### G4.5 — Test moving between floors

1. Connect TALLY-LAPTOP to **JioBharat** → **Test connection** → should pass
2. Move to ground floor → connect **Asus Store** → `ipconfig` (new IP e.g. `.48`) → **Test connection** → should **still pass** (hostname `TALLY-LAPTOP` resolves on the LAN)

Server validation (on WEBSTUDIO-SERVER):

```powershell
cd D:\WEBSTUDIO-IMS\infra\windows
.\validate-production-tally.ps1
```

## G5 — Quick reference (legacy table)

| Concept | Value |
|---------|--------|
| Tally workstation address (hostname) | **`TALLY-LAPTOP`** |
| Port | **`9000`** |
| Company name | Exact name from Tally |
| Enable sync | **Yes** |

---

# PART H — PRODUCTION SETTINGS (after go-live)

## H1 — Backup

**v1.0.2+ Server Setup** auto-detects PostgreSQL `pg_dump` and sets **`POSTGRES_BIN`** + service **PATH** when you run finalize.

After install or any `.env` edit, always run (Administrator):

```powershell
cd D:\WEBSTUDIO-IMS\infra\windows
powershell -ExecutionPolicy Bypass -File .\finalize-server-setup.ps1
```

This copies `config\env\.env` → `apps\backend\.env`, applies NSSM (including `POSTGRES_BIN`, `PATH`, schedulers), and restarts **WEBSTUDIO Server**.

Env-only sync (no migrations):

```powershell
powershell -ExecutionPolicy Bypass -File .\sync-backend-env.ps1 -RestartService
```

Confirm in `.env`:

```env
POSTGRES_BIN=C:\Program Files\PostgreSQL\18\bin
WEBSTUDIO_BACKUP_SCHEDULER=1
```

Main Admin → **Settings → Backup** → **Run manual backup** → confirm **Last backup** updates and a `.tar.gz` appears in `D:\WEBSTUDIO-IMS\backups`.

```powershell
cd D:\WEBSTUDIO-IMS\infra\windows
.\validate-production-backup.ps1
```

| Error | Fix |
|-------|-----|
| **`[WinError 2]`** | Run **finalize** — service needs PostgreSQL on **PATH** |
| Backup folder empty after success message | Check `apps\backend\.env` synced; restart service |

## H2 — Optional AI (Add Laptop specs)

**Recommended:** enter key in app (no server restart):

1. **Settings → Integrations**
2. **Gemini API key** → paste key from [Google AI Studio](https://aistudio.google.com/)
3. **Gemini model** → **`gemini-2.5-flash-lite`** (default in v1.0.2+)
4. Set **Monthly spend cap** in AI Studio (e.g. $2–5)
5. **Save** → **Test AI**

Optional server `.env` fallback:

```env
GEMINI_API_KEY=your_key
```

Then run **finalize-server-setup.ps1**. Settings UI key takes priority over `.env`.

## H3 — Auto-updates (GitHub)

**On the server PC only** — edit **`D:\WEBSTUDIO-IMS\config\env\.env`** (not the Mac dev `.env`):

```env
WEBSTUDIO_GITHUB_REPO=Smarthsingh/WEBSTUDIO-IMS
WEBSTUDIO_GITHUB_TOKEN=ghp_xxxx
WEBSTUDIO_RELEASE_SYNC_SCHEDULER=1
WEBSTUDIO_RELEASE_SYNC_INTERVAL_SECONDS=900
WEBSTUDIO_RELEASE_UPDATES_ROOT=D:\WEBSTUDIO-IMS\Updates
WEBSTUDIO_RELEASE_CHANNEL=stable
APP_ENV=production
```

GitHub PAT: fine-grained token, **Contents read-only** + **Metadata** on `WEBSTUDIO-IMS`.

**Enable background sync** — the server auto-enables this on startup when `WEBSTUDIO_GITHUB_REPO` is set. You can also set it manually in pgAdmin (database **`webstudio`** → Query Tool):

```sql
UPDATE webstudio.system_settings
SET setting_value = 'true', value_type = 'boolean', updated_at = NOW()
WHERE setting_key = 'github_release_sync_enabled';

INSERT INTO webstudio.system_settings (setting_key, setting_value, value_type)
VALUES ('github_release_sync_enabled', 'true', 'boolean')
ON CONFLICT (setting_key)
DO UPDATE SET setting_value = 'true', value_type = 'boolean', updated_at = NOW();
```

**Apply and restart** — copies `.env` to `apps\backend\.env`, updates NSSM, restarts service (PowerShell as Administrator):

```powershell
powershell -ExecutionPolicy Bypass -File "D:\WEBSTUDIO-IMS\infra\windows\finalize-server-setup.ps1"
```

Or env sync + restart only:

```powershell
powershell -ExecutionPolicy Bypass -File "D:\WEBSTUDIO-IMS\infra\windows\sync-backend-env.ps1" -RestartService
```

Desktop → **Settings → Deployment** → **Refresh**. Expect **GitHub repo** filled and **GitHub sync status** not `disabled`.

Manual flow: **Check updates** → **Download** → **Validate** → **Deploy** (admin approval). Desktops poll server (~6h).

## H4 — Final validation

On server:

```powershell
cd D:\WEBSTUDIO-IMS\infra\windows
.\validate-production-network.ps1 -ApiPort 8000
.\validate-production-backup.ps1
```

---

# PART J1 — Recover setup (one command)

If post-install failed on an **older v1.0.1** build, or you changed `.env` / database password:

**PowerShell as Administrator:**

```powershell
powershell -ExecutionPolicy Bypass -File "D:\WEBSTUDIO-IMS\infra\windows\finalize-server-setup.ps1"
```

This script:

1. Prompts for **`webstudio_app` password** (if `DATABASE_URL` still has `CHANGE_ME`)
2. Auto-sets **`POSTGRES_BIN`** (finds `pg_dump.exe` under `Program Files\PostgreSQL`)
3. Clears invalid TLS cert paths (HTTP on port 8000)
4. Syncs `.env` to **`apps\backend\.env`**
5. Applies NSSM environment (**PATH**, schedulers, GitHub vars) and restarts the service
6. Runs Alembic from `database\migrations`
7. Checks `/health/live` and `/health/ready`

> **Always use** `-ExecutionPolicy Bypass -File` — dot-sourcing `.ps1` in a normal PowerShell window may be blocked.

### Common errors

| Error | Fix |
|-------|-----|
| `role is not permitted to log in` | pgAdmin → `webstudio_app` → **Can login?** ON |
| `FileNotFoundError` (SSL cert) | Set `TLS_CERT_PATH=` and `TLS_KEY_PATH=` empty in `.env`, re-run finalize |
| `password authentication failed` | Wrong password — use **webstudio_app**, not postgres |
| `/health/ready` migrations failed | Re-run `finalize-server-setup.ps1` after DB exists |
| **`[WinError 2]` on backup** | Re-run finalize — adds PostgreSQL to service PATH |
| **`running scripts is disabled`** | Use `powershell -ExecutionPolicy Bypass -File .\finalize-server-setup.ps1` |
| **`sync-backend-env.ps1` not found** | Upgrade to **v1.0.2+** or copy from repo `infra\windows\` |
| v1.0.1 long manual NSSM steps | Upgrade to **v1.0.2+** Server Setup, or use finalize script above |

---

# PART I — DAILY USE (staff quick reference)

| Task | How |
|------|-----|
| Open desktop | Start Menu → **WEBSTUDIO Desktop** → wait **Online** → login |
| Open mobile | **WEBSTUDIO IMS** app → login (or **Connect to Server** first time) |
| Scan barcode (phone) | **Inventory** → scan icon → allow Camera |
| Change server (phone) | **Settings → API server** or login **Change** |
| Find laptop | **Ctrl+K** → serial number |
| Server URL (if asked) | `http://192.168.29.100:8000` |
| Wi‑Fi | **JioBharat** or **Asus Store** — not mobile data only |

---

# PART J — TROUBLESHOOTING

| Problem | Fix |
|---------|-----|
| Desktop stuck on "Connecting to server" | Server not running — finish Part C; test browser `/health/live` |
| Server post-install failed | Run **`finalize-server-setup.ps1`** (Part J1); check `install-post.log` |
| `DATABASE_URL` contains `CHANGE_ME` | Post-install prompts for password (v1.0.2+); or run finalize script |
| Service Running but curl fails | Clear `TLS_CERT_PATH=` / `TLS_KEY_PATH=` in `.env`; run finalize script |
| SSL `FileNotFoundError` in api-error.log | TLS paths must be empty for HTTP port 8000 |
| Alembic migration failed | Usually wrong DB password; run finalize script after fixing pgAdmin user |
| `WEBSTUDIO Server` service missing | Re-run Setup.exe as Admin; check post-install log |
| Used public IP `49.43.x.x` | Use `http://192.168.29.100:8000` |
| Ground floor cannot reach server | Jio/Tenda AP isolation **Off**; server firewall script run |
| Server IP changed after reboot | Fix Jio DHCP reservation for MAC `E0:AD:47:31:CA:0A` → `.100` |
| Ping fails between laptops | Normal on Windows — test browser `/health/live` instead |
| `Ethernet 2 media disconnected` on ipconfig | Ignore — unused wired port |
| Smart App Control blocks desktop | Unblock EXE or Run anyway (Part 0C) |
| Logos / addresses missing on login | Install **v1.0.1** desktop — not v1.0.0 |
| Tally fails after moving floor | **Tally workstation address** = host **`TALLY-LAPTOP`**; verify **`netstat` port 9000** on Tally PC |
| Tally **Manual sync only** | Run **finalize-server-setup.ps1** — sets `WEBSTUDIO_TALLY_SCHEDULER=1` |
| Backup **WinError 2** | Run **finalize-server-setup.ps1** (POSTGRES_BIN + PATH) |
| Phone cannot find server | Enter **`http://192.168.29.100:8000`** manually on Connect screen |
| Barcode scan black screen | Allow **Camera** permission; tap **Retry camera** |
| Gemini AI fails first try | Set model **`gemini-2.5-flash-lite`** in Settings → Integrations |
| Desktop Offline | Wi‑Fi Private; correct server URL; server service running |
| `ipconfig /renew` odd messages | Reconnect Wi‑Fi or set manual static `.100` |
| Installed Python 3.14 on server manually | **Not needed** — remove manual venv; use v1.0.1 Server Setup only |

---

# PART K — COMPLETE INSTALL CHECKLIST

| # | Task | Done |
|---|------|------|
| 1 | Download **v1.0.2+** from GitHub Releases | ☐ |
| 2 | Jio: reserve `192.168.29.100` → MAC `E0:AD:47:31:CA:0A` | ☐ |
| 3 | Server `ipconfig` shows `.100` on Wi‑Fi | ☐ |
| 4 | Server Wi‑Fi **Private** | ☐ |
| 5 | PostgreSQL 18 running (`postgresql-x64-18`) | ☐ |
| 6 | Create `webstudio` DB + `webstudio_app` user | ☐ |
| 7 | Remove old `D:\WEBSTUDIO-IMS` if retrying (Part 0C) | ☐ |
| 8 | Install **WEBSTUDIO Server Setup.exe** (Admin); enter `webstudio_app` password at prompt | ☐ |
| 9 | `/health/live` + `/health/ready` OK; run **`finalize-server-setup.ps1`** once | ☐ |
| 10 | **Test manual backup** in Settings → Backup | ☐ |
| 11 | Run `configure-firewall.ps1 -Subnet 192.168.29.0/24` | ☐ |
| 12 | GF laptop: `http://192.168.29.100:8000/health/live` OK | ☐ |
| 13 | Install Desktop v1.0.2+ + Setup Wizard + recovery key saved | ☐ |
| 14 | Install Desktop on all staff laptops | ☐ |
| 15 | Install APK on phones; test Connect + barcode scan | ☐ |
| 16 | TALLY-LAPTOP: XML 9000 + `netstat` + firewall + Settings → Tally | ☐ |
| 17 | Create staff users | ☐ |
| 18 | Backup schedule + validation scripts | ☐ |

---

## Optional deep reference

| Topic | Document |
|-------|----------|
| Full server install | `docs/milestones/m14/INSTALLATION_MANUAL.md` |
| Tally detail | `docs/milestones/m14/TALLY_PRODUCTION_GUIDE.md` |
| User manual | `docs/milestones/m14/USER_MANUAL.md` |
| Administrator | `docs/milestones/m14/ADMINISTRATOR_MANUAL.md` |
| Operations & updates | `docs/milestones/m14/OPERATIONS_MANUAL.md` |

---

*This guide is site-specific for Jio `192.168.29.x` + Tenda AP `Asus Store`. Give staff **Part I** after go-live.*
