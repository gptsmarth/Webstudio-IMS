---
Title: WEBSTUDIO IMS — Deployment Guide
Version: 1.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
Related Documents: docs/PROJECT_BIBLE.md, docs/SYSTEM_ARCHITECTURE.md, docs/product/PRODUCT_REQUIREMENTS.md, adr/ADR-0010-authentication-and-initialization.md
---

# WEBSTUDIO IMS — Deployment Guide

| Attribute | Value |
|-----------|-------|
| **Document ID** | DEPLOY-001 |
| **Version** | 1.0 |
| **Status** | Active — official deployment manual |
| **Audience** | IT staff, installers, Main Admin, operations |
| **Scope** | Version 1 on-premise deployment (Windows server, desktop clients, Android) |

> **Authority:** This document is the official procedure for installing, operating, upgrading, and recovering WEBSTUDIO IMS in production. It must align with [SYSTEM_ARCHITECTURE.md](../SYSTEM_ARCHITECTURE.md), [ADR-0010](../adr/ADR-0010-authentication-and-initialization.md), and [API_SPECIFICATION.md](../api/API_SPECIFICATION.md). This guide describes **procedures only** — not application source code.

---

## Version History

| Version | Date | Author | Summary |
|---------|------|--------|---------|
| 1.0 | 2026-06-27 | WEBSTUDIO IMS Team | Initial official deployment manual. Server install, HTTPS, first-time setup, client onboarding, backup/restore, upgrade, and operations checklists. |

---

## Table of Contents

1. [Server Requirements](#1-server-requirements)
2. [Windows Server Installation](#2-windows-server-installation)
3. [PostgreSQL Installation](#3-postgresql-installation)
4. [Backend Installation](#4-backend-installation)
5. [HTTPS Certificate Installation](#5-https-certificate-installation)
6. [First-Time Setup Wizard](#6-first-time-setup-wizard)
7. [Client Installation](#7-client-installation)
8. [Automatic Server Discovery](#8-automatic-server-discovery)
9. [Manual Server Configuration](#9-manual-server-configuration)
10. [Android Installation](#10-android-installation)
11. [Login](#11-login)
12. [Backup](#12-backup)
13. [Restore](#13-restore)
14. [Software Upgrade](#14-software-upgrade)
15. [Troubleshooting](#15-troubleshooting)
16. [Disaster Recovery](#16-disaster-recovery)
17. [Security Checklist](#17-security-checklist)
18. [Maintenance Checklist](#18-maintenance-checklist)

**Operational procedures (cross-referenced):**

- [Server Startup](#server-startup)
- [Server Shutdown](#server-shutdown)
- [Client Reconnection](#client-reconnection)
- [Certificate Renewal](#certificate-renewal)
- [Database Backup](#database-backup)
- [Restore Verification](#restore-verification)

---

## 1. Server Requirements

### 1.1 Hardware

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **Server PC** | Dedicated workstation — not shared with POS or billing | Windows 11 Pro PC with UPS |
| **CPU** | 4 cores | 8 cores |
| **RAM** | 16 GB | 32 GB |
| **Storage** | 256 GB SSD (OS + database) | 512 GB SSD + separate backup target (NAS) |
| **Network** | Gigabit Ethernet to office Wi-Fi router/switch | Static IP; wired connection preferred |
| **Power** | UPS mandatory | UPS sized for 30+ minutes graceful shutdown |

### 1.2 Software

| Component | Version |
|-----------|---------|
| **Operating system** | Windows 11 Pro |
| **PostgreSQL** | 16.x |
| **Python runtime** | Per [TECH_STACK.md](../TECH_STACK.md) — release artifact includes venv |
| **NSSM** | For Windows Service registration (API and workers) |

### 1.3 Network

| Setting | Requirement |
|---------|-------------|
| **Server IP** | Static local IP (e.g., `192.168.1.100`) or stable hostname |
| **API port** | `8443` HTTPS (configurable via environment) |
| **PostgreSQL** | `localhost:5432` only — **not** exposed to LAN |
| **Firewall** | Inbound **8443/TCP** from store subnet only (e.g., `192.168.1.0/24`) |
| **NTP** | Server clock synchronized — required for audit timestamps and JWT validity |
| **DNS** | Optional local hostname (e.g., `webstudio-server.local`) — certificate SAN must match |

### 1.4 Directory Layout

Create on the server (default root `D:\WEBSTUDIO-IMS\`):

| Path | Purpose |
|------|---------|
| `certs\` | Internal CA, server certificate, private key |
| `logs\` | API and worker log files |
| `backups\` | PostgreSQL dumps, config snapshots, certificate copies |
| `backups\config\` | Environment template exports |
| `backups\certs\` | Certificate backup |
| `exports\` | Excel sync output |
| `exports\archive\` | Pre-overwrite Excel archive copies |

Set NTFS permissions so service accounts can read/write as required; interactive users do not need direct database access.

### 1.5 Pre-Deployment Checklist

- [ ] Static IP assigned and documented
- [ ] UPS connected and tested
- [ ] Store subnet documented for firewall rule
- [ ] Maintenance window agreed (off business hours for initial install)
- [ ] Internal CA strategy decided (new CA or existing org CA)
- [ ] Release artifact version identified and verified (checksum)
- [ ] Backup destination available (local + off-server NAS recommended)

---

## 2. Windows Server Installation

The Dedicated Server PC is installed **once** per business deployment. Client workstations are installed separately (see [Section 7](#7-client-installation)).

### 2.1 Preparation

| Step | Action | Verification |
|------|--------|--------------|
| 1 | Install Windows 11 Pro; apply updates | System stable |
| 2 | Assign static IP; document hostname and IP | Pingable from store subnet |
| 3 | Enable automatic Windows updates (outside business hours) | Update policy set |
| 4 | Configure NTP / reliable time sync | Correct system time |
| 5 | Create directory structure (§1.4) | Paths exist |
| 6 | Create dedicated service accounts (non-interactive) for API and workers | Accounts documented; least privilege |

### 2.2 Windows Services (Production)

| Service | Role | Start Type |
|---------|------|------------|
| PostgreSQL | Database | Automatic |
| WEBSTUDIO API | FastAPI Backend (HTTPS) | Automatic (Delayed Start) |
| WEBSTUDIO Excel Sync | Excel export worker | Automatic (Delayed Start) |
| WEBSTUDIO Tally Sync | Tally integration worker | Automatic (Delayed Start) |

Register API and workers via NSSM (or approved equivalent). Configure **Restart on failure** (3 attempts) for API and workers.

### 2.3 Server Startup

Use this order after reboot, power restoration, or planned maintenance:

| Order | Service | Reason |
|-------|---------|--------|
| 1 | **PostgreSQL** | All application data depends on database availability |
| 2 | **WEBSTUDIO API** | Clients and workers require API |
| 3 | **WEBSTUDIO Excel Sync** | Depends on API |
| 4 | **WEBSTUDIO Tally Sync** | Depends on API |

**Post-startup verification (within 5 minutes):**

1. `GET https://{server}:8443/health` → `200`, status `ok`
2. `GET https://{server}:8443/health/ready` → `200`, database check `ok`
3. Confirm worker services running; review latest log entries for errors
4. Optional: login smoke test from one desktop client

Configure Windows Service dependencies where supported (API depends on PostgreSQL; workers depend on API).

### 2.4 Server Shutdown

Use this order for planned maintenance (backup, upgrade, hardware work):

| Order | Service | Notes |
|-------|---------|-------|
| 1 | **WEBSTUDIO Tally Sync** | Stop accepting new polls |
| 2 | **WEBSTUDIO Excel Sync** | Allow in-flight jobs to complete or cancel gracefully |
| 3 | **WEBSTUDIO API** | Graceful shutdown; drain in-flight HTTP requests |
| 4 | **PostgreSQL** | Stop only after all application connections closed |

**Never** stop PostgreSQL while API or workers are still running.

---

## 3. PostgreSQL Installation

### 3.1 Install

| Step | Action | Verification |
|------|--------|--------------|
| 1 | Install PostgreSQL 16 from official installer | `psql --version` |
| 2 | Register PostgreSQL as Windows Service — Automatic start | Service running |
| 3 | Create database `webstudio` | Connect via `psql` |
| 4 | Create application role `webstudio_app` with least privilege on `webstudio` schema | Role cannot create databases or superuser operations |
| 5 | Restrict PostgreSQL to `localhost` | Port 5432 not reachable from LAN |

### 3.2 Security

- Superuser credentials stored securely — not used by application
- `webstudio_app` used only in `DATABASE_URL` on server
- No direct client or staff access to PostgreSQL — all access via Backend API

### 3.3 Initial Schema

After Backend deployment (Section 4), run database migrations to current head. Migrations create reference data (brands, locations) and set `system_initialized = false`. **No Main Admin user is created by migrations.**

---

## 4. Backend Installation

### 4.1 Deploy Application

| Step | Action | Verification |
|------|--------|--------------|
| 1 | Copy release artifact to server (e.g., `D:\WEBSTUDIO-IMS\app\`) | Version matches release notes |
| 2 | Create Python virtual environment from artifact | Import backend package succeeds |
| 3 | Copy `config/env/.env.example` to server `.env` | File outside Git |
| 4 | Set environment variables (see §4.2) | No secrets in source control |
| 5 | Run `alembic upgrade head` | Migrations current; extensions (`pg_trgm`, `pgcrypto`) applied |
| 6 | Register WEBSTUDIO API Windows Service with TLS flags | Service starts |
| 7 | Register Excel Sync and Tally Sync services | Services start; logs clean |
| 8 | Configure Windows Firewall — port 8443 from store subnet | External port scan confirms restriction |

### 4.2 Required Environment Variables

| Variable | Purpose | Secret |
|----------|---------|--------|
| `DATABASE_URL` | PostgreSQL connection for `webstudio_app` | Yes |
| `JWT_SECRET_KEY` | JWT signing | Yes |
| `API_HOST` | Bind address (typically `0.0.0.0`) | No |
| `API_PORT` | HTTPS port (default `8443`) | No |
| `SSL_CERT_FILE` | Server certificate PEM path | No |
| `SSL_KEY_FILE` | Server private key path | Yes |
| `LOG_LEVEL` | Logging verbosity | No |
| `EXCEL_OUTPUT_PATH` | Excel export directory | No |
| `TALLY_HOST` / `TALLY_PORT` | Tally integration target | No |

### 4.3 Health Verification

| Endpoint | Expected |
|----------|----------|
| `GET /health` | `200` — process alive |
| `GET /health/ready` | `200` — database connected, migrations current |
| `GET /health/version` | Returns API and minimum client version |
| `GET /api/v1/setup/status` | `system_initialized: false` on fresh install |

---

## 5. HTTPS Certificate Installation

HTTPS is **mandatory** for all production deployments ([ADR-0010](../adr/ADR-0010-authentication-and-initialization.md)).

### 5.1 Internal CA and Server Certificate

| Step | Action |
|------|--------|
| 1 | Create or designate an **internal Certificate Authority** |
| 2 | Issue server certificate with **Subject Alternative Names** for hostname and static IP |
| 3 | Store server certificate and private key in `D:\WEBSTUDIO-IMS\certs\` |
| 4 | Configure `SSL_CERT_FILE` and `SSL_KEY_FILE` in server environment |
| 5 | Restart WEBSTUDIO API service |
| 6 | Verify TLS from server: `https://{server}:8443/health` |

### 5.2 Distribute Trust to Clients

| Platform | Action |
|----------|--------|
| **Windows desktop** | Install internal CA root in Trusted Root Certification Authorities |
| **macOS desktop** | Add CA root to System keychain; set trust to "Always Trust" |
| **Android** | Network security config trusts user-installed CA; sideload CA or use documented MDM step |

Clients **must** trust the internal CA before HTTPS login or setup will succeed.

### 5.3 Certificate Renewal

Certificates must be renewed before expiry to avoid client connection failures.

| Step | Action |
|------|--------|
| 1 | **30 days before expiry** — review certificate expiration date |
| 2 | Issue new server certificate from same (or rotated) CA |
| 3 | Backup current cert and key to `backups\certs\` |
| 4 | Replace files in `certs\`; update environment paths if filenames change |
| 5 | Restart WEBSTUDIO API during maintenance window |
| 6 | Verify `https://{server}:8443/health` from each client platform |
| 7 | If CA root rotated, redistribute new CA to **all** clients |

**Rollback:** Restore previous cert/key from `backups\certs\` and restart API.

Document certificate expiry date in the [Maintenance Checklist](#18-maintenance-checklist).

---

## 6. First-Time Setup Wizard

The First-Time Setup Wizard runs when `system_initialized = false` in `system_settings`. The Backend **does not** infer initialization from Main Admin user existence.

### 6.1 When the Wizard Appears

| Condition | Client behaviour |
|-----------|------------------|
| Server freshly migrated; `system_initialized = false` | Any connected client shows wizard after `GET /api/v1/setup/status` |
| `system_initialized = true` | All clients show Login screen only |

The wizard appears **once** per deployment unless the database is intentionally reinitialized.

### 6.2 Wizard Fields

| Field | Requirement |
|-------|-------------|
| **Company Name** | Business display name — persisted as `company_name` |
| **Main Admin Name** | Display name for the administrator |
| **Username** | Unique login identifier (3–64 characters) |
| **Password** | Minimum 10 characters; stored as **bcrypt hash** on server only |
| **Confirm Password** | Must match password |

### 6.3 Completion

On successful submission (`POST /api/v1/setup/initialize`):

1. Main Admin user created (`role = main_admin`, `status = active`)
2. `system_initialized` set to `true`
3. `company_name` saved in `system_settings`
4. Client proceeds to Login screen

### 6.4 Verification

- [ ] `GET /api/v1/setup/status` returns `system_initialized: true`
- [ ] Login with Main Admin credentials succeeds
- [ ] Second setup attempt returns `SYSTEM_ALREADY_INITIALIZED`
- [ ] Additional clients show Login only — not the wizard

### 6.5 Reinitialization (Exceptional)

Re-running the wizard requires deliberate database reset (restore empty database or documented operator procedure). **Never** reinitialize in production without a full backup and business approval.

---

## 7. Client Installation

Client installations **never create users**. Users exist only on the server.

### 7.1 Distribution

| Platform | Installer | Distribution |
|----------|-----------|--------------|
| **Windows** | `.msi` (Electron Builder) | LAN file share or USB |
| **macOS** | `.dmg` | Manual copy and install |
| **Android** | Signed `.apk` | Sideload (see [Section 10](#10-android-installation)) |

### 7.2 Common First-Launch Sequence

1. Install application
2. Trust internal CA (if not pre-installed)
3. Launch application — automatic server discovery begins (§8)
4. Confirm or manually configure server URL (§9)
5. `GET /api/v1/setup/status` — Setup Wizard or Login (§6, §11)
6. Complete setup or login

### 7.3 Client Reconnection

Clients are online-first and do not store business data. When connectivity is lost:

| Situation | Expected behaviour |
|-----------|-------------------|
| **Brief network outage** | Client shows connection error; automatic retry when LAN returns |
| **Access token expired** | Client refreshes token silently using refresh token in OS keychain/keystore |
| **Refresh token invalid / expired** | Client shows Login screen; user re-enters credentials |
| **Server IP or hostname changed** | User opens Manual Server Configuration (§9); Test Connection; Save |
| **Certificate renewed (same CA)** | No client action if same CA root |
| **CA root rotated** | Reinstall trust for new CA on each client; reconnect |
| **Server restored from backup** | Clients reconnect with saved URL; users login normally if `system_initialized = true` |

Stored locally per client: server HTTPS URL, refresh token, theme/window preferences — **not** inventory or user directory data.

---

## 8. Automatic Server Discovery

On **first launch**, clients attempt automatic server discovery on the office LAN.

### 8.1 Discovery Outcomes

| Outcome | Client action |
|---------|---------------|
| **One server found** | Display server information (hostname, address); ask user to **confirm** |
| **Multiple servers found** | Present selection list; user chooses one |
| **None found / timeout** | Automatically switch to [Manual Server Configuration](#9-manual-server-configuration) |

### 8.2 Future Protocol

Version 1 defines the **workflow**. The wire protocol may use mDNS / Bonjour or equivalent — **TBD**. Until implemented, clients may proceed directly to manual configuration when discovery is unavailable.

### 8.3 Verification

- [ ] Confirmed server URL uses `https://` scheme
- [ ] Test Connection succeeds before Save
- [ ] Setup status or Login screen loads after save

---

## 9. Manual Server Configuration

Displayed when discovery fails or when the user chooses to configure manually.

### 9.1 Fields

| Field | Description |
|-------|-------------|
| **Server HTTPS URL** | Full base URL, e.g., `https://192.168.1.100:8443` or `https://webstudio-server.local:8443` |
| **Test Connection** | Validates HTTPS reachability and certificate trust |
| **Save Configuration** | Persists URL to encrypted local config |

### 9.2 Test Connection Checks

- TCP reachability to API port
- TLS handshake succeeds (CA trusted)
- `GET /health` or equivalent reachability probe returns success

### 9.3 Changing Server URL

Main Admin or IT may update the URL from client settings if the server IP or hostname changes. All clients in the store must be updated if the server address changes.

---

## 10. Android Installation

### 10.1 Prerequisites

- Android device on same office Wi-Fi as server
- Internal CA trusted (network security config or user-installed CA per release documentation)
- Signed release `.apk` from approved distribution channel

### 10.2 Install Procedure

| Step | Action |
|------|--------|
| 1 | Enable installation from unknown sources (or deploy via MDM) |
| 2 | Copy and install signed `.apk` |
| 3 | Install internal CA root if required |
| 4 | Launch app — discovery or manual configuration (§8, §9) |
| 5 | Complete First-Time Setup Wizard (if server not initialized) or Login (§11) |

### 10.3 Verification

- [ ] HTTPS health check succeeds from device browser or in-app Test Connection
- [ ] Login and inventory search work on Wi-Fi
- [ ] App does not store inventory data offline after logout

---

## 11. Login

### 11.1 Preconditions

- Client connected to server (`system_initialized = true`)
- User account exists and `status = active`
- HTTPS and CA trust configured

### 11.2 Login Flow

| Step | Action |
|------|--------|
| 1 | User enters **username** and **password** |
| 2 | Client sends `POST /api/v1/auth/login` to Backend |
| 3 | Backend verifies bcrypt hash; issues access and refresh tokens |
| 4 | Client stores refresh token in **OS keychain/keystore**; access token in memory |
| 5 | User proceeds to authorized screens per role |

### 11.3 Role Summary

| Role | Access |
|------|--------|
| **Main Admin** | Full system; user management; settings; integrations |
| **Admin** | Inventory, movement, reports per PRD matrix |
| **Salesperson** | Search, view, move inventory per PRD §17.2 |

### 11.4 Password Management

| Action | Who |
|--------|-----|
| **Change own password** | Any authenticated user |
| **Reset password** | **Main Admin only** |
| **Self-service recovery (email, OTP)** | **Not available** Version 1 |

Forgotten passwords require Main Admin reset — document this in staff training.

### 11.5 Session Behaviour

- Access token: short-lived (default 15 minutes)
- Refresh token: longer-lived (default 7 days); rotated on refresh
- Inactivity timeout: configurable by Main Admin
- Account lockout after configurable failed login attempts

### 11.6 Logout

User logout revokes refresh token server-side. Client clears in-memory access token and keychain refresh token.

---

## 12. Backup

### 12.1 Database Backup

| Aspect | Policy |
|--------|--------|
| **Method** | `pg_dump` of `webstudio` database |
| **Schedule** | Daily via Windows Scheduled Task (off-peak hours) |
| **Manual trigger** | Main Admin or operator via documented procedure |
| **Location** | `D:\WEBSTUDIO-IMS\backups\` |
| **Off-server copy** | Robocopy or equivalent to LAN NAS — **recommended** |
| **Retention** | Minimum 30 days online; business policy may extend |

### 12.2 Additional Assets

| Asset | Method | Location |
|-------|--------|----------|
| **Excel exports** | Archive copy before overwrite | `exports\archive\` |
| **Configuration** | Export `.env` template snapshot (no secrets in unsecured shares) | `backups\config\` |
| **TLS certificates** | Secure copy of server cert, key, CA root | `backups\certs\` |
| **Release artifact** | Keep previous installer/version alongside upgrade | Documented version store |

### 12.3 Backup Naming

Use timestamps in dump filenames (e.g., `webstudio_YYYYMMDD_HHMMSS.dump`) for unambiguous restore selection.

### 12.4 Pre-Upgrade Backup

Always take a verified backup **before** any software upgrade or migration (§14).

---

## 13. Restore

### 13.1 When to Restore

- Hardware failure
- Database corruption
- Failed upgrade requiring rollback
- Disaster recovery (§16)

### 13.2 Restore Procedure

| Step | Action |
|------|--------|
| 1 | [Shut down services](#server-shutdown) in correct order |
| 2 | Select latest **verified** backup (§[Restore Verification](#restore-verification)) |
| 3 | Restore `pg_dump` to PostgreSQL (`webstudio` database) |
| 4 | If schema drift expected, run `alembic upgrade head` after restore |
| 5 | Restore configuration and certificates from backup if needed |
| 6 | [Start services](#server-startup) in correct order |
| 7 | Verify row counts and spot-check serial numbers |
| 8 | Smoke test: health, login, search, single inventory read |
| 9 | Notify Main Admin; document incident |

### 13.3 Restore Verification

A backup is **not considered valid** until restore verification succeeds.

| Frequency | Action |
|-----------|--------|
| **Monthly** | Automated or manual restore to **isolated** database instance (not production) |
| **After restore test** | Compare table row counts; spot-check serial numbers against known samples |
| **On failure** | Alert Main Admin; do not rely on that backup set until issue resolved |

Failed verification blocks reliance on the affected backup set for disaster recovery until corrected.

### 13.4 Partial Recovery

- **Configuration only:** Restore `backups\config\` and `certs\`; restart services
- **Excel only:** Restore from `exports\archive\` — does not restore PostgreSQL authority
- **PostgreSQL is authoritative** for inventory — Excel is derived

---

## 14. Software Upgrade

Perform upgrades during agreed maintenance windows, off business hours when possible.

### 14.1 Server Upgrade (API + Workers)

| Step | Action |
|------|--------|
| 1 | Announce maintenance window |
| 2 | [Shut down services](#server-shutdown) |
| 3 | Full [database backup](#12-backup) |
| 4 | Deploy new Python release artifact |
| 5 | Review release notes for migration requirements |
| 6 | Run `alembic upgrade head` on staging copy first; then production |
| 7 | [Start services](#server-startup) |
| 8 | Verify health, readiness, login, critical workflows |
| 9 | Monitor logs for 24 hours |

**Rollback:** Restore previous artifact and pre-upgrade database backup if migration fails.

### 14.2 Database Migrations

- Forward-only in production
- Test every migration against a copy of production data before applying
- Never skip migration versions

See [migration-runbook.md](database/migration-runbook.md).

### 14.3 Desktop Upgrade

| Step | Action |
|------|--------|
| 1 | Distribute new `.msi` / `.dmg` via LAN share |
| 2 | Staff install over existing version (or IT remote install) |
| 3 | Verify `X-Client-Version` accepted by API |
| 4 | Rollback: reinstall previous installer if needed |

### 14.4 Android Upgrade

| Step | Action |
|------|--------|
| 1 | Distribute new signed `.apk` |
| 2 | Sideload on each device |
| 3 | Verify login and connectivity |
| 4 | Rollback: reinstall previous APK |

### 14.5 Version Compatibility

Clients send `X-Client-Version` header. API exposes minimum supported version via `/health`. Upgrade clients before or with server if breaking changes are documented in release notes.

---

## 15. Troubleshooting

### 15.1 Server Not Reachable

| Symptom | Check |
|---------|-------|
| Client cannot connect | Server powered on; static IP unchanged; Wi-Fi same subnet |
| Connection refused | WEBSTUDIO API service running; port 8443 listening |
| Firewall block | Windows Firewall rule allows store subnet on 8443 |
| Wrong URL | Manual configuration — verify `https://` and port |

### 15.2 TLS / Certificate Errors

| Symptom | Check |
|---------|-------|
| Certificate untrusted | Internal CA installed on client |
| Certificate expired | [Renew certificate](#certificate-renewal) |
| Hostname mismatch | Certificate SAN includes server IP and hostname |

### 15.3 Setup Wizard Issues

| Symptom | Check |
|---------|-------|
| Wizard will not submit | Password match; username length; API logs |
| `SYSTEM_ALREADY_INITIALIZED` | System already set up — use Login |
| Wizard reappears unexpectedly | Database restored to uninitialized state — investigate restore source |

### 15.4 Login Failures

| Symptom | Check |
|---------|-------|
| `SYSTEM_NOT_INITIALIZED` | Complete First-Time Setup Wizard first |
| `INVALID_CREDENTIALS` | Username/password; caps lock |
| `ACCOUNT_LOCKED` | Wait for lockout duration or Main Admin unlock |
| `ACCOUNT_DISABLED` | Main Admin must re-enable account |

### 15.5 Database Issues

| Symptom | Check |
|---------|-------|
| `/health/ready` returns 503 | PostgreSQL service; `DATABASE_URL`; disk space |
| Slow performance | Disk space; connection count; PostgreSQL logs |

### 15.6 Sync Worker Issues

| Symptom | Check |
|---------|-------|
| Excel not updating | Excel Sync service running; `EXCEL_OUTPUT_PATH` writable; job logs |
| Tally events missing | Tally Sync service; `TALLY_HOST`; network to Tally machine |

### 15.7 Logs

| Service | Location |
|---------|----------|
| WEBSTUDIO API | `D:\WEBSTUDIO-IMS\logs\` |
| Excel Sync | `D:\WEBSTUDIO-IMS\logs\` |
| Tally Sync | `D:\WEBSTUDIO-IMS\logs\` |
| PostgreSQL | PostgreSQL data log directory |

---

## 16. Disaster Recovery

### 16.1 Scenarios

| Scenario | Primary recovery |
|----------|------------------|
| **Server hardware failure** | Replace hardware; restore latest verified backup |
| **Database corruption** | Restore from latest verified `pg_dump` |
| **Ransomware / compromise** | Isolate network; restore from off-server verified backup; rotate all secrets |
| **Certificate compromise** | Issue new cert; rotate CA if needed; redistribute trust |
| **Complete site loss** | Out of Version 1 scope — cloud DR **TBD** |

### 16.2 Recovery Time Objectives

| Metric | Target |
|--------|--------|
| **RTO** | **TBD** with business — document agreed hours |
| **RPO** | Daily backup minimum; off-server copy recommended |

### 16.3 Recovery Procedure Summary

1. Procure replacement server (or repair hardware)
2. Install Windows, PostgreSQL, Backend per Sections 2–4
3. Restore certificates and configuration from backup
4. [Restore database](#132-restore-procedure) from latest **verified** dump
5. [Start services](#server-startup)
6. Reconnect all clients (§[Client Reconnection](#client-reconnection))
7. Parallel run / reconciliation with Excel if extended outage — **TBD** with business
8. Post-incident review and checklist update

### 16.4 Main Admin Lockout

If all Main Admin passwords are lost:

- Requires database operator intervention (password hash reset via controlled procedure)
- **Prevention:** maintain at least two Main Admin accounts; secure password record with business owner

No email or self-service recovery in Version 1.

---

## 17. Security Checklist

Use at initial deployment and quarterly review.

### 17.1 Network and Transport

- [ ] HTTPS enforced on API — no HTTP on LAN in production
- [ ] PostgreSQL bound to localhost only
- [ ] Firewall allows 8443 from store subnet only
- [ ] No public internet exposure of API or database
- [ ] NTP synchronized on server

### 17.2 Certificates and Secrets

- [ ] Internal CA documented; root securely stored
- [ ] Server certificate SAN matches hostname and IP
- [ ] Certificate expiry date documented; renewal procedure assigned
- [ ] `JWT_SECRET_KEY` and database passwords in environment only — not in Git
- [ ] Service accounts use strong passwords; not shared with staff

### 17.3 Authentication and Users

- [ ] First-Time Setup completed; default/seed admin **not** present
- [ ] Main Admin passwords strong; at least two Main Admin accounts recommended
- [ ] Unused accounts disabled — not deleted
- [ ] Lockout threshold configured
- [ ] Staff trained: password reset via Main Admin only

### 17.4 Application and Data

- [ ] Clients do not store business data locally
- [ ] Backups encrypted at rest on NAS (**recommended**)
- [ ] Off-server backup copy exists and is tested
- [ ] Audit log retention policy documented
- [ ] Excel file share permissions restrict write to sync service only

### 17.5 Operations

- [ ] Backup schedule active
- [ ] Monthly restore verification passing
- [ ] Windows updates applied on schedule
- [ ] Incident response contact documented

---

## 18. Maintenance Checklist

### 18.1 Daily (Automated)

- [ ] PostgreSQL backup completed
- [ ] Backup copy to NAS succeeded (if configured)
- [ ] Services running (monitoring or scheduled health check)

### 18.2 Weekly (Operator / Main Admin)

- [ ] Review API and worker logs for errors
- [ ] Review Excel sync and Tally integration status
- [ ] Confirm disk space adequate on server

### 18.3 Monthly

- [ ] [Restore verification](#restore-verification) completed and logged
- [ ] Certificate expiry check (renew if within 30 days)
- [ ] Review disabled user accounts
- [ ] Review failed login / lockout patterns in audit log

### 18.4 Per Upgrade

- [ ] Pre-upgrade backup verified
- [ ] Staging migration test passed
- [ ] Post-upgrade smoke test documented
- [ ] Client versions compatible with API

### 18.5 Annual

- [ ] Disaster recovery drill (full restore to test environment)
- [ ] Review firewall rules and static IP documentation
- [ ] Review service account passwords (rotation policy **TBD**)
- [ ] UPS battery test

---

## References

| Document | Path |
|----------|------|
| Project Bible | [docs/PROJECT_BIBLE.md](../PROJECT_BIBLE.md) |
| System Architecture | [docs/SYSTEM_ARCHITECTURE.md](../SYSTEM_ARCHITECTURE.md) |
| Product Requirements | [docs/product/PRODUCT_REQUIREMENTS.md](../product/PRODUCT_REQUIREMENTS.md) |
| API Specification | [docs/api/API_SPECIFICATION.md](../api/API_SPECIFICATION.md) |
| ADR-0010 Authentication & Initialization | [adr/ADR-0010-authentication-and-initialization.md](../adr/ADR-0010-authentication-and-initialization.md) |
| Migration Runbook | [database/migration-runbook.md](database/migration-runbook.md) |
| Technology Stack | [docs/TECH_STACK.md](../TECH_STACK.md) |

---

> **Document Authority:** This guide is the official deployment manual for WEBSTUDIO IMS Version 1. Update this document when deployment procedures change; significant architectural changes require ADR amendment.

*WEBSTUDIO IMS Team — 2026*
