---
Title: Enterprise Network Troubleshooting Guide
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12D
---

# Enterprise Network Troubleshooting Guide — M12D

Symptoms and fixes for the office LAN topology (multi-SSID, mobile Tally, business-hours server).

---

## Quick diagnostics

| Tool | Where |
|------|-------|
| Network administrator wizard | Desktop → Settings → Backup → Recovery Center |
| Connection diagnostics | Desktop/Flutter connection screen (6 stages) |
| API | `GET /health/ready`, `GET /api/v1/discovery/health` |
| Server logs | `D:\WEBSTUDIO-IMS\logs\webstudio-api.log` |

---

## Clients show offline after server reboot

**Expected:** Auto-reconnect within 15 seconds — no user action.

**If not recovering:**

1. Confirm server PC is on and `WEBSTUDIO Server` service running  
2. From client browser/curl: `http://<server-hostname>:8443/health/live`  
3. Desktop: verify saved server uses **hostname** not old IP (Settings → re-test connection)  
4. Check firewall on server: `configure-firewall.ps1`  
5. Confirm phone/desktop on **same LAN** as server (not guest Wi‑Fi)  

---

## mDNS discovery finds nothing

**Cause:** Multicast blocked between APs/VLANs or Bonjour not installed on Windows server.

**Fix:**

1. Use manual connection with hostname: `http://webstudio-server.local:8443`  
2. Add internal DNS A record → server static IP  
3. Set `WEBSTUDIO_DISCOVERY_CANDIDATES` on server  
4. Enable mDNS reflector on router if SSIDs are isolated  
5. Install Bonjour Print Services on Windows server (optional)  

---

## Different Wi‑Fi SSIDs (ground vs first floor)

**Requirement:** Both SSIDs must reach the same server IP (same subnet or routed).

**Test:** Ping server IP from each floor. If ping fails, fix router/AP bridging — not an IMS bug.

---

## Tally sync fails after laptop moved

**Expected:** Warning in Tally dashboard; sync retries automatically.

**Fix:**

1. Confirm Tally is running on laptop  
2. Ping laptop hostname from server  
3. Test TCP 9000: `Test-NetConnection LENOVO-TALLY -Port 9000` (PowerShell on server)  
4. Update IMS Tally host to current hostname if laptop was renamed  
5. Background probe runs every 120s — check Tally operational panel  

---

## DHCP changed server IP

**Clients using hostname:** Should auto-reconnect (DNS/mDNS refresh).

**Clients using raw IP:** Update saved URL once to hostname; future changes are automatic.

---

## Android / iPhone cannot connect

1. Same subnet as server (not mobile data only)  
2. Install APK with correct server URL from QR onboarding  
3. App polls health every 15s — wait after morning server boot  
4. iOS: local network permission granted  

---

## Firewall / port issues

| Check | Command / action |
|-------|------------------|
| API listening | Server: `netstat -an | findstr 8443` |
| Windows firewall | Run `infra/windows/configure-firewall.ps1` |
| PostgreSQL local | `netstat -an | findstr 5432` (127.0.0.1 only) |
| Tally from server | Outbound TCP 9000 to laptop IP/hostname |

---

## Administrator wizard failures

| Check failed | Typical fix |
|--------------|-------------|
| Database | Start PostgreSQL service |
| API | Start WEBSTUDIO Server service |
| Migrations | `alembic upgrade head` |
| Backup folders | Create `D:\WEBSTUDIO-IMS\backups`, fix NTFS permissions |
| Tally | Expected warning if laptop offline — not a blocker |
| AI | Add API key or disable enrichment |

---

## Escalation data to collect

1. Network wizard export (screenshot or JSON from `/api/v1/network/admin/report`)  
2. Connection diagnostic stages from client  
3. Last 200 lines of `webstudio-api.log`  
4. Server IP, hostname, SSID names, router model  

---

## Related documents

- [NETWORK_REPORT.md](./NETWORK_REPORT.md)  
- [DEPLOYMENT_REPORT.md](./DEPLOYMENT_REPORT.md)  
- [docs/integrations/tally-erp9/troubleshooting.md](../../integrations/tally-erp9/troubleshooting.md)
