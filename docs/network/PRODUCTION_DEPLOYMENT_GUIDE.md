---
Title: Production Deployment Guide — Network Discovery
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Related Documents: docs/deployment/DEPLOYMENT_GUIDE.md
---

# Production Deployment Guide — Network Discovery

Extends the main [Deployment Guide](../deployment/DEPLOYMENT_GUIDE.md) with Milestone 11X zero-configuration networking.

## Pre-Deployment Checklist

- [ ] Office subnet documented (`NETWORK_REQUIREMENTS.md`)
- [ ] Server IP reserved (DHCP reservation or static)
- [ ] `WEBSTUDIO_SERVER_NAME` set to stable hostname
- [ ] Firewall allows TCP API port + UDP 5353 on LAN
- [ ] PostgreSQL reachable from backend only
- [ ] First-time setup completed (company name populated for discovery)

## Server Deployment

### Environment

```bash
export WEBSTUDIO_SERVER_NAME=WEBSTUDIO-SERVER
export WEBSTUDIO_MDNS_ENABLED=1
export WEBSTUDIO_BUILD_VERSION=$(git rev-parse --short HEAD)
```

### Verify Advertisement

After start, from another LAN machine:

```bash
dns-sd -B _webstudio-ims._tcp   # macOS
# or browse via Desktop/Mobile discovery UI
curl http://<server>:8000/api/v1/discovery/health
```

Expected JSON fields: `online`, `company_name`, `backend_version`, `database_status`.

### Disable mDNS (air-gapped / manual-only sites)

```bash
export WEBSTUDIO_MDNS_ENABLED=0
```

Manual connection continues to work.

## Client Rollout

### Desktop (Windows / macOS)

1. Distribute installer via existing channel.
2. Users launch app — discovery runs automatically.
3. IT runbook: fallback URL `http://WEBSTUDIO-SERVER.local:8000`.

### Mobile (Android / iOS)

1. Distribute APK / TestFlight / MDM.
2. iOS: approve local network prompt on first launch.
3. Android: ensure `INTERNET` + Wi‑Fi connected.

## Hostname-Based Deployment Pattern

| Layer | Setting |
|-------|---------|
| OS hostname | `WEBSTUDIO-SERVER` |
| mDNS | `WEBSTUDIO-SERVER.local` |
| Saved client URL | `http://WEBSTUDIO-SERVER.local:8000` |
| DHCP | Reservation to current IP |

When IP changes, clients resolve hostname at connect time — no reconfiguration.

## Multi-Site / VLAN

If server and clients are on different VLANs without mDNS reflection:

1. Disable reliance on auto-discovery for that site, **or**
2. Deploy DNS A record + manual first connect, **or**
3. Configure mDNS gateway (Avahi reflector / Bonjour Gateway)

## Tally Workstation

Tally remains on a designated PC. Backend resolves Tally host at runtime (`LENOVO-TALLY.local`). Clients do not need Tally network access.

## Monitoring

- `GET /health/ready` — database + disk
- `GET /api/v1/discovery/health` — discovery-facing metadata
- Client connection diagnostics — staged failure identification

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| Discovery empty | Same LAN; check AP isolation; verify `WEBSTUDIO_MDNS_ENABLED` |
| `.local` fails on Windows | Install Bonjour Print Services or use short hostname + internal DNS |
| Stale saved server IP | Remove and re-save, or use hostname URL (auto-refresh) |
| Stage: API Compatibility | Upgrade client or adjust `min_*_version` settings |
| Stage: Authentication Endpoint | Backend reachable but setup API error — check logs |

## Rollback

Set `WEBSTUDIO_MDNS_ENABLED=0` and distribute manual server URL to users. No database migration required.

## Security

- Discovery TXT records contain metadata only
- API authentication unchanged (JWT after login)
- Use HTTPS/TLS in production when certificates are deployed (manual URL `https://...` still supported)
