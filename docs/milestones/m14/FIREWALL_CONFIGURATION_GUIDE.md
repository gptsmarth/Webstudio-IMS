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

The helper reads `API_PORT` from the installation's `config\env\.env`. The default is TCP `8000`.

---

## 2. Automated configuration

After verifying the service locally, run the bundled helper in **Administrator Windows PowerShell**. Adjust the installation path if needed.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'D:\WEBSTUDIO-IMS\infra\windows\configure-firewall.ps1' -Enable
```

The helper detects a single eligible Private IPv4 address and its connected subnet. For an explicit selection, use the actual server IP, office CIDR, and app port. These values are examples.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'D:\WEBSTUDIO-IMS\infra\windows\configure-firewall.ps1' -Enable -ServerIp '10.20.30.10' -Subnet '10.20.30.0/24' -ApiPort 8000
```

The helper creates or updates **WEBSTUDIO IMS - Office LAN** on the selected interface. It scopes inbound TCP to the local IPv4 address and the connected private subnet or a narrower subnet on that connection. Edge traversal is blocked. Keep PostgreSQL on loopback and leave router port forwarding off. Configure optional mDNS discovery separately for UDP `5353` on the trusted staff subnet.

If the active office profile is Public, open **Windows Settings → Network & internet**, select the trusted office connection, and set **Network profile type → Private**. Then rerun the helper. Keep untrusted networks Public. [Microsoft network profile settings](https://support.microsoft.com/en-us/windows/experience/connectivity-networking/essential-network-settings-and-tasks-in-windows#make-a-network-public-or-private)

Run this from **Administrator Windows PowerShell** to disable the managed API rule.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'D:\WEBSTUDIO-IMS\infra\windows\configure-firewall.ps1' -Disable
```

When changing the app port, update `API_PORT`, apply the server configuration, and rerun the helper. When changing a DHCP reservation, verify the server received the new IP before rerunning the helper.

---

## 3. Verify the rule

```powershell
Get-NetFirewallRule -DisplayName 'WEBSTUDIO IMS - Office LAN' | Format-Table DisplayName, Enabled, Profile, Direction, Action
```

Expect an enabled **Private**, **Inbound**, **Allow** rule. From a staff laptop, check `/health/ready` using the server's LAN address and verify TCP `5432` is inaccessible. [Microsoft firewall rule parameters](https://learn.microsoft.com/en-us/powershell/module/netsecurity/set-netfirewallrule)

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
| API works on server browser (`localhost`) but not from desktop | Firewall or API bound to `127.0.0.1` only | Check `API_HOST` and run `configure-firewall.ps1 -Enable` |
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
| `infra/windows/configure-firewall.ps1` | Manage the scoped inbound API rule |
| `infra/windows/validate-production-network.ps1` | Post-config LAN probe script |
| `docs/milestones/m12h/NETWORKING_GUIDE.md` | Full networking topology |
