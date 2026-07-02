---
Title: Network Requirements
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
---

# Network Requirements — WEBSTUDIO IMS

## Office Topology

```text
                    [Internet]
                        |
                   [Office Router]
                    /    |    \
            [Wi‑Fi AP] [Switch] [Server - Backend]
               /  \       |
         [Desktop] [Mobile devices]
```

**Requirement:** Clients and backend must share a **routable L2/L3 LAN** where unicast HTTP (TCP port 8000 or configured port) and **multicast mDNS** (UDP 5353) are permitted.

## Supported Network Modes

| Mode | Supported | Notes |
|------|-----------|-------|
| Ethernet | ✓ | Preferred for server |
| Wi‑Fi | ✓ | Same SSID/subnet as server |
| Multiple APs (same SSID) | ✓ | Enable AP client isolation **off** |
| DHCP | ✓ | Use hostname-based URLs for stability |
| Static IP | ✓ | Document IP in runbook |
| DHCP reservation | ✓ | Recommended for server |
| Guest Wi‑Fi | ✗ | Usually blocks LAN + mDNS |

## Access Point Recommendations

1. **Disable client isolation** (AP isolation / guest barrier) on the staff SSID.
2. Use a **single flat subnet** for IMS devices (e.g. `192.168.10.0/24`).
3. Prefer **one SSID** for staff devices; avoid VLAN separation unless mDNS reflector is configured.
4. Enterprise Wi‑Fi: if mDNS does not cross VLANs, use **DNS A record** (`webstudio-server.office.local`) or manual IP with saved servers.

## Ports and Protocols

| Traffic | Protocol | Port | Direction |
|---------|----------|------|-----------|
| API | TCP HTTP/HTTPS | 8000 (default) | Client → Server |
| mDNS | UDP multicast | 5353 | Bidirectional on LAN |
| PostgreSQL | TCP | 5432 | Server only (not clients) |
| Tally | TCP | 9000 (typical) | **Server → Tally PC only** |

## Firewall (Server Host)

Allow inbound:

- TCP `8000` (or configured API port) from office subnet
- UDP `5353` from office subnet (mDNS)

Block inbound from WAN.

## DHCP Reservation Guide

1. Identify server MAC address.
2. In router/DHCP server, create reservation → fixed IP (e.g. `192.168.10.10`).
3. Set `WEBSTUDIO_SERVER_NAME=WEBSTUDIO-SERVER` on the backend host.
4. Clients can connect via `WEBSTUDIO-SERVER.local` or reserved IP.

## Static IP Guide

1. Assign IP, mask, gateway on server OS.
2. Register internal DNS **optional** but recommended: `WEBSTUDIO-SERVER → 192.168.10.10`.
3. Document in [PRODUCTION_DEPLOYMENT_GUIDE.md](./PRODUCTION_DEPLOYMENT_GUIDE.md).

## Hostname-Based Deployment (Recommended)

Use **`WEBSTUDIO-SERVER.local`** (mDNS) or internal DNS hostname instead of raw IP. Saved servers store hostname and refresh IP automatically when DHCP changes.

## mDNS Privacy

Advertisement exposes only: server name, company name, versions, port, environment, build — no credentials.

## Platform Notes

| Platform | mDNS browse | mDNS advertise |
|----------|-------------|----------------|
| Windows Desktop | ✓ (Electron main) | N/A (client) |
| macOS Desktop | ✓ | N/A |
| Android | ✓ (Bonsoir / NSD) | N/A |
| iOS | ✓ (Bonjour + local network permission) | N/A |
| Backend Linux | N/A | ✓ (Python zeroconf) |
