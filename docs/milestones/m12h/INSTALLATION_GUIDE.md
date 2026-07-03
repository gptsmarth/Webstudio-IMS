---
Title: Installation Guide — WEBSTUDIO IMS
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12H
---

# Installation Guide

Install WEBSTUDIO IMS from production release artifacts. Verify checksums before install.

---

## 1. Before you begin

| Requirement | Detail |
|-------------|--------|
| Release bundle | `release/v{VERSION}/` from `pnpm release:prepare` or CI |
| Checksums | `shasum -a 256 -c checksums.sha256` |
| Manifest | `version-manifest.json` — note Alembic head |
| Network | Gigabit LAN; see [Networking Guide](NETWORKING_GUIDE.md) |
| Hardware | Dedicated Windows 11 Pro server PC (see [Server Guide](SERVER_GUIDE.md)) |

---

## 2. Install order

```
1. Server (Windows) + PostgreSQL
2. First-time setup (Main Admin)
3. Office deployment wizard
4. Desktop clients (admin PC first, then floor)
5. Mobile (Android / iOS)
6. Tally configuration
```

---

## 3. Windows Server

### Option A — Installer (recommended)

1. Run `WEBSTUDIO Server Setup.exe` from release artifacts.
2. Default install root: `D:\WEBSTUDIO-IMS`
3. Installer runs: PostgreSQL check, migrations, NSSM service install.
4. Service name: **WEBSTUDIO Server** (Automatic Delayed Start).

### Option B — Manual

See [DEPLOY-001](../../deployment/DEPLOYMENT_GUIDE.md) sections 2–4 and [Server Guide](SERVER_GUIDE.md).

### Verify

```powershell
sc query "WEBSTUDIO Server"
curl http://localhost:8000/health/live
```

---

## 4. First-time setup

1. On admin desktop, connect to `http://{server-ip}:8000`
2. Complete **System Setup**: company, Main Admin, recovery key
3. Confirm recovery key offline
4. Complete **Office Deployment Wizard** (detect → save → summary)

---

## 5. Windows Desktop

1. Run `WEBSTUDIO Desktop Setup.exe`
2. Install for all users (per-machine)
3. Launch from Start Menu
4. Server discovered via mDNS or enter `http://{server-ip}:8000`
5. Log in as Main Admin

Build reference: [M12C Installer Guide](../m12c/INSTALLER_GUIDE.md)

---

## 6. macOS Desktop

1. Open `WEBSTUDIO Desktop.dmg`
2. Drag to Applications
3. Connect to server URL (same as Windows)

---

## 7. Android

1. Enable **Install from unknown sources** (or use MDM)
2. Copy `WEBSTUDIO IMS.apk` to device
3. Install APK
4. Open app → discover server → login

See [Android Guide](ANDROID_GUIDE.md)

---

## 8. iOS

1. Install via TestFlight or signed IPA (requires Apple developer setup)
2. Open app → server URL → login

See [iOS Guide](IOS_GUIDE.md)

---

## 9. Post-install validation

| Check | Pass |
|-------|------|
| Server health | `/health/ready` returns ready |
| Setup complete | Login works for Main Admin |
| Desktop inventory | List loads |
| Mobile login | Same user can authenticate |
| Backup | Manual backup succeeds |
| Tally test | Settings → Tally → Test Connection (when Tally PC on) |

Use [M12E Validation Guide](../m12e/VALIDATION_GUIDE.md) for Tally go-live.

---

## 10. Uninstall

| Component | Action |
|-----------|--------|
| Desktop | Settings → Apps → Uninstall |
| Server | `infra/windows/uninstall-webstudio-service.ps1` (preserves data if requested) |
| Database | Manual — backup first |
