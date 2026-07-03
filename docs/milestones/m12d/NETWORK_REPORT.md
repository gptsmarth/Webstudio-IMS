---
Title: Enterprise Network Report
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12D
---

# Enterprise Network Report — WEBSTUDIO IMS

**Office topology (M12D):**

```
Ground Floor
    ↓
Access Point(s) — multiple SSIDs OK on same LAN
    ↓
LAN
    ↓
First Floor Router
    ↓
Dedicated Server PC (Windows 11 Pro)
    ↓
├── Desktop clients (Ethernet / Wi‑Fi)
├── Android phones (Wi‑Fi)
├── iPhones (Wi‑Fi)
└── Movable Lenovo Tally laptop (Wi‑Fi, may change floor / SSID)
```

---

## Design principles

| Principle | Implementation |
|-----------|----------------|
| Same LAN | All SSIDs must route to one subnet/VLAN for store devices |
| Static or reserved IP | Server uses fixed address; clients save **hostname** not stale IP |
| mDNS discovery | Server advertises `_webstudio-ims._tcp` on UDP 5353 |
| No manual reconnect | Desktop/Flutter refresh hostname every 15s and on outage |
| Tally mobility | Server re-resolves Tally hostname each sync + background probe |
| DHCP tolerance | Saved server hostname re-resolved via DNS/mDNS on every reconnect |

---

## Ports and protocols

| Service | Port | Direction | Notes |
|---------|------|-----------|-------|
| WEBSTUDIO API | 8443 (prod) / 8000 (dev) | Inbound to server from LAN | TCP |
| PostgreSQL | 5432 | localhost only | Not exposed to Wi‑Fi |
| mDNS | 5353 | LAN broadcast/multicast | Client discovery |
| Tally XML | 9000 (default) | Server → Tally laptop | TCP when Tally running |

Configure with `infra/windows/configure-firewall.ps1` on the server.

---

## Client discovery flow

1. **mDNS browse** (4.5s) — finds `WEBSTUDIO-SERVER.local` or custom name  
2. **Saved servers** — hostname re-resolved before probe  
3. **Fallback candidates** — from `WEBSTUDIO_DISCOVERY_CANDIDATES` on server + local defaults  
4. **Six-stage diagnostics** — host → reachability → HTTP → ready → version → setup status  

---

## Server-side services

| Service | Purpose |
|---------|---------|
| `MdnsAdvertisementService` | LAN advertisement |
| `NetworkValidationService` | Administrator wizard checks |
| `TallyConnectivityService` | Runtime DNS + TCP + XML probe |
| `tally_connectivity_probe_loop` | Background probe every 120s (persisted scheduler) |

---

## Administrator validation API

| Method | Endpoint | Auth |
|--------|----------|------|
| POST | `/api/v1/network/admin/validate` | `settings:view` or `dashboard:system_status` |
| GET | `/api/v1/network/admin/report` | Same |

**Desktop UI:** Settings → Backup → Recovery Center → **Network wizard**

---

## Multi-SSID guidance

- Ground floor and first floor SSIDs may differ **if** the router bridges them to the same `192.168.x.0/24` (or routed) network.  
- Use **DHCP reservation** for server and optional fixed hostname for Tally laptop.  
- If mDNS does not cross subnets, register internal DNS `A` record pointing to server static IP.  
- Clients store hostname — IP changes after DHCP renewal do not require user action.

---

## Related documents

- [DEPLOYMENT_REPORT.md](./DEPLOYMENT_REPORT.md)  
- [TROUBLESHOOTING_GUIDE.md](./TROUBLESHOOTING_GUIDE.md)  
- [docs/network/NETWORK_REQUIREMENTS.md](../../network/NETWORK_REQUIREMENTS.md)
