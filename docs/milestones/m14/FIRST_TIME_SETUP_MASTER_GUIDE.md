---
Title: WEBSTUDIO IMS — Complete Customer Office Setup Guide
Version: 3.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-03
Milestone: 14
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
  https://github.com/Smarthsingh/WEBSTUDIO-IMS/releases → v1.0.0

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
2. Click release **`v1.0.0`**
3. Under **Assets**, download:

| File | Install on |
|------|------------|
| **`WEBSTUDIO Server Setup.exe`** | Server PC (`WEBSTUDIO-SERVER`) |
| **`WEBSTUDIO Desktop Setup.exe`** | Every staff laptop |
| **`WEBSTUDIO IMS.apk`** | Android phones |
| **`checksums.sha256`** | Optional verify |

If Releases is empty, check **Actions → Enterprise Release** finished green, then refresh Releases.

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

## C1 — Prepare Windows

1. Windows 11 Pro, updated.
2. Computer name: **`WEBSTUDIO-SERVER`**
3. Confirm IP: **`192.168.29.100`** (`ipconfig`)
4. Wi‑Fi profile: **Private**

## C2 — Run installer

1. **Create PostgreSQL database first** (pgAdmin or psql):
   - Database: `webstudio`
   - User: `webstudio_app` with password (note for `.env`)
2. **`WEBSTUDIO Server Setup.exe`** → **Run as administrator**
3. Install path: **`D:\WEBSTUDIO-IMS`**
4. Wait for post-install (bundled Python + NSSM, migrations, Windows service)
   - Post-install window stays visible; errors log to `logs\install-post.log`
   - PostgreSQL service name is **auto-detected** (`postgresql-x64-16`, `-18`, etc.)

## C3 — Verify services

```powershell
Get-Service postgresql*
Get-Service "WEBSTUDIO Server"
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

## C4 — Edit `.env`

File: **`D:\WEBSTUDIO-IMS\config\env\.env`**

```env
APP_ENV=production
API_HOST=0.0.0.0
API_PORT=8000
WEBSTUDIO_DATA_ROOT=D:\WEBSTUDIO-IMS
WEBSTUDIO_DISCOVERY_CANDIDATES=192.168.29.100,WEBSTUDIO-SERVER
```

Keep installer-generated `JWT_SECRET` and `DATABASE_URL`.

Restart:

```powershell
Restart-Service "WEBSTUDIO Server"
```

## C5 — Run firewall script

```powershell
cd D:\WEBSTUDIO-IMS\infra\windows
.\configure-firewall.ps1 -ApiPort 8000 -Subnet 192.168.29.0/24
.\validate-production-network.ps1 -ApiPort 8000
```

## C6 — Test from ground floor

On laptop connected to **Asus Store**, browser:

```text
http://192.168.29.100:8000/health/live
```

Must return OK. If yes → both floors reach server.

---

# PART D — FIRST DESKTOP + SETUP WIZARD

On any admin laptop (1st or ground floor).

## D1 — Install desktop

1. Run **`WEBSTUDIO Desktop Setup.exe`**
2. Launch from Start Menu

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

1. Install **`WEBSTUDIO Desktop Setup.exe`**
2. Server URL: **`http://192.168.29.100:8000`**
3. Wi‑Fi → **Private**
4. Log in with user account (Main Admin creates users in **Settings → Users**)

**No static IP. No GitHub token. No `.env` on laptops.**

---

# PART F — PHONES (Android)

| Phone (examples) | DHCP IP (changes) |
|------------------|-------------------|
| Smarth-s-S22 | e.g. `.233` |
| Galaxy-M14 | e.g. `.87` |

1. Copy **`WEBSTUDIO IMS.apk`** to phone
2. Install (allow unknown apps if asked)
3. Server URL: **`http://192.168.29.100:8000`**
4. Works on **JioBharat** and **Asus Store**

---

# PART G — TALLY-LAPTOP (moves 1st floor ↔ ground floor)

## G1 — Your Tally machine

| Field | Value |
|-------|--------|
| Computer name | **`TALLY-LAPTOP`** (you set this) |
| Current IP (example) | `192.168.29.176` — **will change** when switching Wi‑Fi |
| Gateway | `192.168.29.1` |
| Wi‑Fi | JioBharat or Asus Store |

**Never enter `192.168.29.176` in WEBSTUDIO** — use hostname instead.

## G2 — Tally ERP 9 on TALLY-LAPTOP

1. Install Tally ERP 9
2. Enable **XML / ODBC** on port **9000**
3. Note exact **company name** as shown in Tally

## G3 — Firewall on TALLY-LAPTOP

**PowerShell as Administrator** on TALLY-LAPTOP:

```powershell
New-NetFirewallRule -DisplayName "Tally XML 9000" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 9000 -Profile Private
```

Wi‑Fi on both floors → **Private**.

## G4 — WEBSTUDIO Tally settings (Main Admin desktop)

**Settings → Tally:**

| Field | Value |
|-------|--------|
| Enable integration | **Yes** |
| Host | **`TALLY-LAPTOP`** |
| Port | **`9000`** |
| Company name | Exact name from Tally |

Click **Test connection**.

## G5 — Test moving between floors

1. Connect TALLY-LAPTOP to **JioBharat** → Test connection → pass
2. Move to ground floor → connect **Asus Store** → `ipconfig` (new IP e.g. `.48`) → Test connection → **still pass** (hostname resolves)

Server validation (on WEBSTUDIO-SERVER):

```powershell
cd D:\WEBSTUDIO-IMS\infra\windows
.\validate-production-tally.ps1
```

---

# PART H — PRODUCTION SETTINGS (after go-live)

## H1 — Backup

Main Admin → **Settings → Backup** → enable schedule → **Test backup**

```powershell
cd D:\WEBSTUDIO-IMS\infra\windows
.\validate-production-backup.ps1
```

## H2 — Optional AI (Add Laptop specs)

Server `.env`:

```env
GEMINI_API_KEY=your_key
```

Restart service. Desktop → **Settings → Integrations** → Test AI.

## H3 — Auto-updates (optional, later)

Server `.env` only:

```env
WEBSTUDIO_GITHUB_REPO=Smarthsingh/WEBSTUDIO-IMS
WEBSTUDIO_GITHUB_TOKEN=ghp_xxxx
WEBSTUDIO_RELEASE_SYNC_SCHEDULER=1
```

Main Admin → enable GitHub sync → **Deployment Center** → approve each deploy.

Desktops poll server (~6h) — user clicks Install when prompted.

## H4 — Final validation

On server:

```powershell
cd D:\WEBSTUDIO-IMS\infra\windows
.\validate-production-network.ps1 -ApiPort 8000
.\validate-production-backup.ps1
```

---

# PART I — DAILY USE (staff quick reference)

| Task | How |
|------|-----|
| Open desktop | Start Menu → **WEBSTUDIO Desktop** → wait **Online** → login |
| Open mobile | **WEBSTUDIO IMS** app → login |
| Find laptop | **Ctrl+K** → serial number |
| Server URL (if asked) | `http://192.168.29.100:8000` |
| Wi‑Fi | **JioBharat** or **Asus Store** — not mobile data only |

---

# PART J — TROUBLESHOOTING

| Problem | Fix |
|---------|-----|
| Used public IP `49.43.x.x` | Use `http://192.168.29.100:8000` |
| Ground floor cannot reach server | Jio/Tenda AP isolation **Off**; server firewall script run |
| Server IP changed after reboot | Fix Jio DHCP reservation for MAC `E0:AD:47:31:CA:0A` → `.100` |
| Ping fails between laptops | Normal on Windows — test browser `/health/live` instead |
| `Ethernet 2 media disconnected` on ipconfig | Ignore — unused wired port |
| Tally fails after moving floor | Use host **`TALLY-LAPTOP`** not IP; check port 9000 firewall on Tally PC |
| Desktop Offline | Wi‑Fi Private; correct server URL; server service running |
| `ipconfig /renew` odd messages | Reconnect Wi‑Fi or set manual static `.100` |

---

# PART K — COMPLETE INSTALL CHECKLIST

| # | Task | Done |
|---|------|------|
| 1 | Download EXEs from GitHub Releases v1.0.0 | ☐ |
| 2 | Jio: reserve `192.168.29.100` → MAC `E0:AD:47:31:CA:0A` | ☐ |
| 3 | Server `ipconfig` shows `.100` on Wi‑Fi | ☐ |
| 4 | Server Wi‑Fi **Private** | ☐ |
| 5 | Install WEBSTUDIO Server on WEBSTUDIO-SERVER | ☐ |
| 6 | Edit `.env` + restart service | ☐ |
| 7 | Run `configure-firewall.ps1 -Subnet 192.168.29.0/24` | ☐ |
| 8 | GF laptop: `http://192.168.29.100:8000/health/live` OK | ☐ |
| 9 | Install Desktop + Setup Wizard + recovery key saved | ☐ |
| 10 | Install Desktop on all staff laptops | ☐ |
| 11 | Install APK on phones | ☐ |
| 12 | TALLY-LAPTOP: XML 9000 + firewall + Settings host name | ☐ |
| 13 | Create staff users | ☐ |
| 14 | Backup schedule + validation scripts | ☐ |

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
