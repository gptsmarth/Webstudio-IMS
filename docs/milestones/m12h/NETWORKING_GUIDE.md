---
Title: Networking Guide — WEBSTUDIO IMS
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12H
---

# Networking Guide

LAN networking for WEBSTUDIO IMS: server, clients, and Tally billing PC.

---

## 1. Topology overview

```
Internet (optional)
       │
  Office Router
   ├── Wi‑Fi SSID: Store-Floor
   ├── Wi‑Fi SSID: Office
   └── Ethernet
         ├── Dedicated Server PC (WEBSTUDIO)
         ├── Desktop PCs
         ├── Tally Laptop (billing)
         └── Mobile devices (Wi‑Fi)
```

See [Networking Diagrams](diagrams/NETWORKING_DIAGRAMS.md).

---

## 2. IP addressing

| Device | Recommendation |
|--------|----------------|
| **Server** | DHCP reservation or static IP (e.g. `192.168.1.100`) |
| **Tally laptop** | DHCP reservation by MAC (hostname stable) |
| **Clients** | DHCP — discovery finds server |

Office Deployment Wizard recommends **DHCP Reservation** when mDNS is active, else **Static IP** on server.

---

## 3. Ports

| Port | Protocol | Direction | Service |
|------|----------|-----------|---------|
| 8000 | TCP | Inbound to server | WEBSTUDIO API |
| 5432 | TCP | Localhost only | PostgreSQL |
| 5353 | UDP | LAN | mDNS discovery |
| 9000 | TCP | Server → Tally laptop | Tally XML |

Run `infra/windows/configure-firewall.ps1` on the server.

---

## 4. Server discovery

| Method | When |
|--------|------|
| **mDNS** | Same subnet; service `_webstudio-ims._tcp.local.` |
| **Saved URL** | Clients remember last server |
| **Manual URL** | `http://192.168.1.100:8000` |
| **Candidate list** | `WEBSTUDIO_DISCOVERY_CANDIDATES` env / office deployment |

Desktop polls every 15s when disconnected (M12D).

---

## 5. Multi-SSID / multi-floor

All store SSIDs must route to the **same LAN/VLAN** as the server.

**Common showroom layout:** server on **ground floor**, Tally laptop on **first floor** — fully supported. Floor only matters for physical cabling; apps and Tally sync use IP/hostname on the shared subnet.

1. Settings → Backup → Recovery Center → **Network wizard**
2. Validate server, database, API, Tally, backup paths
3. Fix router AP isolation if clients cannot discover server

See [M12D Troubleshooting](../m12d/TROUBLESHOOTING_GUIDE.md).

---

## 6. Tally laptop mobility

- Tally PC may move between floors on Wi‑Fi
- Use **hostname** not IP for `tally_host` in settings
- Connectivity probe retries every 120s
- Sync resumes automatically when Tally returns

---

## 7. Security

- Keep PostgreSQL on localhost only
- Do not port-forward API to internet without VPN
- Use HTTPS with internal CA if required (DEPLOY-001 §5)
- Segment guest Wi‑Fi from inventory LAN

---

## 8. Related documents

- [docs/network/NETWORK_REQUIREMENTS.md](../../network/NETWORK_REQUIREMENTS.md)
- [docs/network/ZERO_CONFIGURATION_SETUP_GUIDE.md](../../network/ZERO_CONFIGURATION_SETUP_GUIDE.md)
- [M12D Network Report](../m12d/NETWORK_REPORT.md)
