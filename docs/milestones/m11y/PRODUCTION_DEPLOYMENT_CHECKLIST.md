---
Title: Production Deployment Checklist
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 11Y
Related Documents: docs/network/PRODUCTION_DEPLOYMENT_GUIDE.md, docs/deployment/DEPLOYMENT_GUIDE.md
---

# Production Deployment Checklist

Operational checklist for deploying WEBSTUDIO IMS to a **production office LAN**. Use before first go-live and before each major upgrade.

---

## Phase 1 — Infrastructure

### Network

- [ ] Staff devices and server on same LAN subnet (or mDNS/DNS configured)
- [ ] AP client isolation **disabled** on staff Wi‑Fi
- [ ] Firewall: inbound TCP **8000** (API) from office subnet only
- [ ] Firewall: UDP **5353** (mDNS) on LAN if using auto-discovery
- [ ] DHCP reservation or static IP for server documented
- [ ] Hostname registered (`WEBSTUDIO-SERVER.local` or internal DNS)

### Server host

- [ ] OS patches applied (Windows Server / Linux / macOS server)
- [ ] PostgreSQL 15+ installed and secured (local access only)
- [ ] Disk space ≥20% free on data and backup volumes
- [ ] NTP/time sync enabled (JWT and audit timestamps)

---

## Phase 2 — Backend Configuration

Copy from `config/env/.env.example` — **never commit production `.env`**.

- [ ] `APP_ENV=production`
- [ ] `JWT_SECRET=` random string **≥32 bytes**
- [ ] `DATABASE_URL=` production PostgreSQL connection string
- [ ] `CORS_ORIGINS=` desktop dev server origins if needed; empty or specific for Electron `file://` / custom protocol in M12
- [ ] `LOG_LEVEL=INFO`
- [ ] `LOG_JSON=true`
- [ ] `API_HOST=0.0.0.0` (or LAN bind address)
- [ ] `API_PORT=8000` (or chosen port)
- [ ] `WEBSTUDIO_SERVER_NAME=WEBSTUDIO-SERVER` (recommended)
- [ ] `WEBSTUDIO_MDNS_ENABLED=1` (or `0` for manual-only sites)
- [ ] `WEBSTUDIO_BUILD_VERSION` / `WEBSTUDIO_GIT_COMMIT` set from release tag
- [ ] TLS cert paths set if terminating HTTPS on uvicorn

### Database

- [ ] Run `alembic upgrade head` → revision **`0033_tally_connectivity`**
- [ ] Verify `SELECT version_num FROM webstudio.alembic_version;`
- [ ] Database user least privilege (not superuser)

### Startup verification

- [ ] `GET /health/live` → 200
- [ ] `GET /health/ready` → database `ok`
- [ ] `GET /api/v1/discovery/health` → `online: true`
- [ ] mDNS service visible from client subnet (if enabled)

---

## Phase 3 — First-Time Setup

- [ ] Launch desktop or mobile client
- [ ] Auto-discovery finds server OR manual URL configured
- [ ] Complete setup wizard (company name, admin user)
- [ ] **Recovery key** recorded offline by Main Admin
- [ ] Confirm recovery key acknowledgment in wizard
- [ ] Login as Main Admin succeeds

---

## Phase 4 — Client Deployment

### Desktop (Windows / macOS)

- [ ] Install from M12 packaged artifact (not dev Vite server)
- [ ] Confirm **Preview mode not available** in production build (M12 gate)
- [ ] Connection diagnostics all stages ✓
- [ ] Session restore after restart works
- [ ] Export/report permissions verified for standard roles

### Mobile (Android / iOS)

- [ ] Install release-signed APK/IPA (not debug)
- [ ] iOS local network permission granted
- [ ] Camera permission for barcode flow tested
- [ ] Offline queue sync after reconnect tested
- [ ] Mandatory update gate tested against `/api/v1/version`

---

## Phase 5 — Integrations

### Tally (if used)

- [ ] Tally host configured as hostname (e.g. `LENOVO-TALLY.local`)
- [ ] Backend can reach Tally port (typically 9000) — **clients do not**
- [ ] Connection test stages pass in Settings → Tally
- [ ] Test sync run completes

### Backup

- [ ] Backup schedule configured (not `disabled`)
- [ ] Manual backup completes and download works
- [ ] Backup manifest includes company metadata
- [ ] Restore drill on staging copy (recommended before prod)

### AI enrichment (optional)

- [ ] Gemini API key configured in settings if used
- [ ] Keys not exposed in discovery or public endpoints

---

## Phase 6 — Security Review

- [ ] Default admin password changed from setup wizard value
- [ ] Integration API keys rotated from any dev values
- [ ] Audit log retention policy configured
- [ ] Session list / revoke tested for stolen device scenario
- [ ] PostgreSQL not exposed to WAN
- [ ] Server SSH/RDP restricted to admin IPs

---

## Phase 7 — Upgrade / Rollback

### Upgrade (existing installation)

- [ ] Full backup taken before upgrade
- [ ] Stop API → `alembic upgrade head` → start API
- [ ] Client apps updated to matching semver
- [ ] Smoke test: login, inventory view, sale create, report export

### Rollback

- [ ] Previous backup available
- [ ] Restore procedure documented and tested on staging
- [ ] Client downgrade path documented (reinstall prior version)

---

## Phase 8 — Post Go-Live

- [ ] Monitor `/health/ready` (automated if M12 adds ops tooling)
- [ ] Review `webstudio-client.log` on desktop for errors (first 48h)
- [ ] Confirm backup job ran on schedule
- [ ] User training: connection retry, saved servers, recovery key storage

---

## Emergency Contacts & References

| Topic | Document |
|-------|----------|
| Network | `docs/network/NETWORK_REQUIREMENTS.md` |
| Zero-config | `docs/network/ZERO_CONFIGURATION_SETUP_GUIDE.md` |
| Tally troubleshooting | `docs/integrations/tally-erp9/troubleshooting.md` |
| Known issues | `docs/milestones/m11/KNOWN_ISSUES_REPORT.md` |

---

## Deployment Sign-Off

| Field | Value |
|-------|-------|
| Site name | |
| Server IP/hostname | |
| Backend version | |
| Schema revision | |
| Deploy date | |
| Deployed by | |
| Recovery key escrow location | |
