---
Title: Enterprise Deployment Report
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12D
---

# Enterprise Deployment Report — Office LAN (M12D)

Deployment model for a **single-store office** with a dedicated server PC powered on during business hours (M12B) and mobile Tally on a Lenovo laptop.

---

## Physical layout

| Location | Equipment | Network |
|----------|-----------|---------|
| First floor | Dedicated server PC | Wired Ethernet to router (recommended) |
| First floor | Router / gateway | DHCP server, optional VLAN |
| Ground / First floor | Wi‑Fi access point(s) | Same LAN as server |
| Mobile | Tally laptop | Wi‑Fi — may roam between floors |
| Staff desks | Desktop PCs | Ethernet or Wi‑Fi |
| Floor staff | Android / iPhone | Store Wi‑Fi |

---

## Server deployment checklist

- [ ] Static IP or DHCP reservation for server (document in runbook)  
- [ ] `WEBSTUDIO Server Setup.exe` installed (M12C)  
- [ ] PostgreSQL 16 running as Windows service  
- [ ] `WEBSTUDIO Server` service — Automatic Delayed Start  
- [ ] `configure-firewall.ps1` — allow API port from store subnet  
- [ ] TLS certificate installed (recommended for production API port 8443)  
- [ ] `WEBSTUDIO_DISCOVERY_CANDIDATES` set in `.env` with server hostname/IP  
- [ ] `WEBSTUDIO_TALLY_CONNECTIVITY_PROBE=1` enabled  
- [ ] Backup folder on `D:\WEBSTUDIO-IMS\backups` verified writable  
- [ ] Run **Network administrator wizard** — all checks passed or warnings documented  

---

## Client deployment checklist

| Client | Artifact | Connection |
|--------|----------|------------|
| Desktop | WEBSTUDIO Desktop Setup.exe | Auto-discovery or saved hostname |
| Android | WEBSTUDIO IMS.apk | QR / manual URL once; auto-reconnect after |
| iPhone | IPA / sideload | Same as Android |

**No per-device reconfiguration** when server powers on each morning.

---

## Tally laptop deployment

1. Install Tally ERP 9 on Lenovo laptop  
2. Enable Tally as server; note XML port (default 9000)  
3. Set **Windows hostname** (e.g. `LENOVO-TALLY`) — use hostname in IMS settings, not IP  
4. Allow inbound TCP 9000 on laptop firewall when Tally is running  
5. Configure IMS: Tally host = `LENOVO-TALLY.local` or hostname  
6. Laptop may sleep, change SSID, or move floor — sync resumes when reachable  

---

## Environment variables (server)

```env
WEBSTUDIO_DISCOVERY_CANDIDATES=192.168.1.100,webstudio-server.local
WEBSTUDIO_TALLY_CONNECTIVITY_PROBE=1
WEBSTUDIO_TALLY_SCHEDULER=1
MDNS_ENABLED=true
API_HOST=0.0.0.0
API_PORT=8443
```

---

## Daily operations (business hours)

| Time | Action |
|------|--------|
| Morning | Power on server PC → services start automatically |
| Business | Clients reconnect within ~15s if server was off |
| Evening | Graceful shutdown (M12B) → power off server |
| Tally | Leave laptop on when syncing; may disconnect overnight without breaking IMS |

---

## Validation sign-off

Run Network wizard and record:

- Overall status  
- Server LAN IP  
- mDNS active  
- Tally connectivity (warning OK if laptop offline after hours)  
- Backup folder writable  

---

## Related documents

- [NETWORK_REPORT.md](./NETWORK_REPORT.md)  
- [TROUBLESHOOTING_GUIDE.md](./TROUBLESHOOTING_GUIDE.md)  
- [M12B Business Hours Guide](../m12b/BUSINESS_HOURS_DEPLOYMENT_GUIDE.md)
