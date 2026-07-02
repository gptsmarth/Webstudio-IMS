---
Title: Zero-Configuration Setup Guide
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
---

# Zero-Configuration Setup Guide

This guide walks through plug-and-play deployment for a typical office LAN.

## Prerequisites

- All devices on the **same subnet** (same Wi‑Fi SSID or wired VLAN)
- Multicast/mDNS allowed between client devices and the server (see [NETWORK_REQUIREMENTS.md](./NETWORK_REQUIREMENTS.md))
- Backend, Desktop, and Mobile apps installed

## Step 1 — Install the Server

1. Deploy the WEBSTUDIO IMS backend on the office server or NUC.
2. Ensure PostgreSQL is running and migrations are applied.
3. Start the API (default port **8000**).
4. On startup the server automatically advertises `_webstudio-ims._tcp` on the LAN.

Optional: set a stable advertisement name:

```bash
export WEBSTUDIO_SERVER_NAME=WEBSTUDIO-SERVER
```

Complete first-time setup (company name) — this name appears in discovery results.

## Step 2 — Install Desktop Clients

1. Launch **WEBSTUDIO IMS Desktop**.
2. The app scans the LAN (~4 seconds).
3. Discovered servers appear with **Company Name**, **Server Name**, **Version**, and **Status**.
4. Click **Connect** on your server.
5. If nothing appears, use **Saved servers** or enter the address manually, then **Retry automatic discovery**.

Supported address formats:

- `192.168.1.10`
- `WEBSTUDIO-SERVER`
- `WEBSTUDIO-SERVER.local`
- Full URL: `http://WEBSTUDIO-SERVER.local:8000`

## Step 3 — Install Mobile Clients

1. Open the app → **Connect to Server**.
2. LAN scan runs automatically on first launch.
3. Tap **Connect** on the discovered server.
4. Fallback: manual entry or saved servers (same formats as desktop).

**iOS:** Local network permission is requested on first discovery (Info.plist usage string).

**Android:** Ensure Wi‑Fi is connected; emulator uses `10.0.2.2` for host machine backend.

## Step 4 — Verify

After connection, sign in or complete setup. Connection diagnostics should show all stages ✓.

Quick server check from any browser on the LAN:

```
http://<server-ip>:8000/api/v1/discovery/health
```

## Troubleshooting Quick Reference

| Symptom | Action |
|---------|--------|
| No servers found | Confirm same LAN; check firewall multicast; try manual hostname |
| Connect fails at Host Resolution | Verify DNS or use `.local` name / IP |
| Connect fails at Backend Health | Check PostgreSQL; review `/health/ready` |
| Worked yesterday, IP changed | Use hostname-based URL; saved servers auto-refresh IP |

See [NETWORK_REQUIREMENTS.md](./NETWORK_REQUIREMENTS.md) and [PRODUCTION_DEPLOYMENT_GUIDE.md](./PRODUCTION_DEPLOYMENT_GUIDE.md) for office topology and static/DHCP guidance.
