---
Title: Production Infrastructure Checklist
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14B
Related Documents:
  - docs/milestones/m14/NETWORK_VALIDATION_REPORT.md
  - docs/milestones/m14/FIREWALL_CONFIGURATION_GUIDE.md
  - docs/milestones/m12h/NETWORKING_GUIDE.md
---

# Production Infrastructure Checklist (M14B)

Use this checklist during **production commissioning** on the store LAN. Mark each item **Pass / Fail / N/A** and attach evidence (screenshots, command output, or API report JSON).

---

## A. Server network (IT)

| ID | Check | Pass criteria | Evidence |
|----|-------|---------------|----------|
| NET-01 | Static server IP or DHCP reservation | Server LAN IP is fixed and documented in Office Deployment or `WEBSTUDIO_DISCOVERY_CANDIDATES` | Router DHCP table / `ipconfig` |
| NET-02 | LAN accessibility | `http://<server-ip>:8000/api/v1/health/live` returns HTTP 200 from another LAN device | Browser or `curl` from desktop |
| NET-03 | Multi-SSID / multi-AP | All store Wi‑Fi SSIDs route to the **same subnet/VLAN** as the server; AP isolation disabled | Router/AP config screenshot |
| NET-04 | Same subnet | Clients receive IPs in the same routed range as the server (e.g. `192.168.1.0/24`) | `ipconfig` / phone Wi‑Fi details |
| NET-05 | Windows Firewall | Inbound TCP **8000** and UDP **5353** allowed from store subnet | `configure-firewall.ps1` output |
| NET-06 | Port availability | API **8000** listening; PostgreSQL **5432** localhost only; mDNS **5353** on LAN | Validation wizard or PowerShell script |
| NET-07 | PostgreSQL connectivity | `SELECT 1` succeeds; Alembic at head; port not exposed on LAN | Network wizard database check |
| NET-08 | API reachability | `/api/v1/health/live` and `/api/v1/discovery/health` OK on LAN URL | API responses saved |
| NET-09 | Server discovery | mDNS active **or** discovery candidate URLs configured | Discovery health JSON |
| NET-10 | Automatic reconnect | After server restart, desktop/mobile reconnect without manual URL entry | Restart test log |

---

## B. Client devices (store admin)

| ID | Check | Pass criteria | Evidence |
|----|-------|---------------|----------|
| CLI-01 | Desktop connectivity | Windows/macOS desktop app reaches server on store LAN | Connection diagnostics screenshot |
| CLI-02 | Android connectivity | Flutter Android app on store Wi‑Fi discovers or uses saved server | Login screen / About |
| CLI-03 | iOS connectivity | Flutter iOS app on store Wi‑Fi discovers or uses saved server | Login screen / About |
| CLI-04 | Roaming test | Move phone between floors/SSIDs; app stays connected or auto-reconnects within 30s | Notes from walk test |
| CLI-05 | Tally laptop (if enabled) | Server reaches Tally XML port when laptop is on store LAN | Network wizard Tally check |

---

## C. Automated validation commands

### API (authenticated — Network Admin)

```http
POST /api/v1/network/admin/validate?scope=production
GET  /api/v1/network/admin/report?scope=production
```

Desktop path: **Settings → Backup → Recovery Center → Network administrator wizard → Run validation**

### Windows server (elevated PowerShell)

```powershell
cd C:\WEBSTUDIO\ims\infra\windows
.\configure-firewall.ps1 -ApiPort 8000 -Subnet 192.168.1.0/24
.\validate-production-network.ps1 -ApiPort 8000
```

---

## D. Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| IT / Installer | | | |
| Store administrator | | | |
| WEBSTUDIO engineer | | | |

**Overall result:** ☐ Pass — production LAN ready &nbsp; ☐ Fail — remediate before 14C
