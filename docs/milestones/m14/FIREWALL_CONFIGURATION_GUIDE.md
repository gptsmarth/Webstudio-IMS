---
Title: Windows Firewall Configuration Guide
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14B
Related Documents:
  - docs/milestones/m12h/NETWORKING_GUIDE.md
  - infra/windows/configure-firewall.ps1
  - infra/windows/validate-production-network.ps1
---

# Windows Firewall Configuration Guide (M14B)

WEBSTUDIO IMS runs on a **dedicated Windows 11 Pro server PC** on the store LAN. Windows Defender Firewall must allow **LAN clients** to reach the API and mDNS discovery while keeping the database **localhost-only**.

---

## 1. Port matrix

| Port | Protocol | Direction | Bind | Purpose |
|------|----------|-----------|------|---------|
| **8000** | TCP | **Inbound** from store subnet | Server LAN interface | WEBSTUDIO REST API |
| **5353** | UDP | **Inbound** from store subnet | Server LAN interface | mDNS / Bonjour discovery |
| **5432** | TCP | **Localhost only** | `127.0.0.1` | PostgreSQL — **never** expose to LAN |
| **9000** | TCP | **Outbound** server → Tally laptop | N/A on server inbound | Tally XML (billing PC) |

Default API port is **8000** (see `WEBSTUDIO_API_PORT` in production `.env`). If you use a custom port, pass `-ApiPort` to both scripts below.

---

## 2. Automated configuration (recommended)

Run **elevated PowerShell** on the server:

```powershell
cd C:\WEBSTUDIO\ims\infra\windows
.\configure-firewall.ps1 -ApiPort 8000 -Subnet 192.168.1.0/24
```

This creates or refreshes:

| Rule display name | Action |
|-------------------|--------|
| `WEBSTUDIO IMS API Inbound` | Allow TCP inbound on API port from `-Subnet` |
| `WEBSTUDIO IMS mDNS` | Allow UDP 5353 inbound from `-Subnet` |

**Subnet:** Use your store LAN CIDR (e.g. `192.168.1.0/24`). Restrict to the office subnet — do not use `Any` in production.

---

## 3. Verify rules

```powershell
Get-NetFirewallRule -DisplayName "WEBSTUDIO IMS*" | Format-Table DisplayName, Enabled, Direction, Action
```

Expected: two **Enabled** **Allow** **Inbound** rules.

---

## 4. Production validation

After firewall configuration and service start:

```powershell
.\validate-production-network.ps1 -ApiPort 8000
```

Or use the API production scope:

```http
POST /api/v1/network/admin/validate?scope=production
```

**Pass criteria for `windows_firewall` check:**

- API port reachable on the server **LAN IP** (not only `127.0.0.1`)
- `windows_firewall` check **passed** or **warning** with documented remediation
- PostgreSQL **not** reachable from another LAN device on port 5432

---

## 5. Manual rule creation (fallback)

If PowerShell execution policy blocks scripts:

1. Open **Windows Defender Firewall with Advanced Security**
2. **Inbound Rules → New Rule**
3. **Port → TCP → Specific local ports:** `8000`
4. **Allow the connection**
5. Scope: **Remote IP** = store subnet (e.g. `192.168.1.0/255.255.255.0`)
6. Name: `WEBSTUDIO IMS API Inbound`
7. Repeat for **UDP 5353** (mDNS)

---

## 6. Common failures

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| API works on server browser (`localhost`) but not from desktop | Firewall or API bound to `127.0.0.1` only | Run `configure-firewall.ps1`; set `WEBSTUDIO_API_HOST=0.0.0.0` / `API_HOST=0.0.0.0` |
| Desktop works on server PC but fails on Wi‑Fi laptops after restart | Client still using `http://127.0.0.1:8000` (localhost is the laptop itself) | Open **Connection** setup and save `http://<server-lan-ip>:8000` (e.g. `http://192.168.29.100:8000`). Restart desktop — URL must persist. Startup also auto-discovers via mDNS + LAN probes. |
| Mobile / desktop should find server without typing IP | Discovery only ran on Connection screen before | Startup bootstrap + reconnect now auto-fetch via mDNS, saved servers, and shop LAN candidates (`192.168.29.100`, etc.) |
| Mobile shows `Startup failed: type '_Map<dynamic, dynamic>'…` | Hive cache typed-map cast bug on session restore | Install mobile build that opens Hive boxes as untyped and uses safe JSON map coercion |
| mDNS discovery fails | UDP 5353 blocked or AP isolation enabled | Firewall rule + disable client isolation on APs |
| PostgreSQL exposed on LAN | Misconfigured PostgreSQL `listen_addresses` | Keep `localhost`; validation should flag non-local bind |
| Wrong subnet in rule | Store uses `10.0.0.0/24` but rule says `192.168.1.0/24` | Re-run script with correct `-Subnet` |

---

## 7. Security notes

- Do **not** open PostgreSQL (5432) to the LAN.
- Do **not** expose the API to the public internet without TLS and a reverse proxy (out of scope for standard store deployment).
- Restrict inbound rules to the **store subnet CIDR**, not `Any`.
- Re-run validation after Windows updates or firewall policy changes.

---

## 8. Related files

| File | Purpose |
|------|---------|
| `infra/windows/configure-firewall.ps1` | Create inbound API + mDNS rules |
| `infra/windows/validate-production-network.ps1` | Post-config LAN probe script |
| `docs/milestones/m12h/NETWORKING_GUIDE.md` | Full networking topology |
