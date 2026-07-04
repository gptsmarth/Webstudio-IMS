---
Title: Desktop Deployment Guide — Production
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14E
Related Documents:
  - docs/milestones/m14/CLIENT_ACCEPTANCE_CHECKLIST.md
  - docs/milestones/m12c/INSTALLER_GUIDE.md
  - docs/milestones/m12h/NETWORKING_GUIDE.md
---

# Desktop Deployment Guide (M14E)

Production guide for deploying **WEBSTUDIO Desktop** on staff Windows and macOS PCs.

**Prerequisites:** M14A server commissioned; M14B networking validated.

---

## 1. Artifacts

| Platform | Artifact | Build command |
|----------|----------|---------------|
| **Windows** | `WEBSTUDIO Desktop Setup.exe` | `pnpm desktop:package:win` |
| **macOS** | `WEBSTUDIO Desktop.dmg` | `pnpm desktop:package:mac` |

Output directory: `apps/desktop/release/desktop/`

Distribute from enterprise release catalog on WEBSTUDIO Server — clients **never** download from GitHub.

---

## 2. Windows — install EXE

1. Copy `WEBSTUDIO Desktop Setup.exe` to the staff PC (USB, share, or Deployment Center download).
2. Run installer (per-machine NSIS).
3. Launch from **Start Menu** or desktop shortcut.
4. On first launch, allow Windows Firewall if prompted (outbound to server only).

**Signed builds (recommended):** Configure `WIN_CSC_LINK` and `WIN_CSC_KEY_PASSWORD` in GitHub before release so Smart App Control does not block staff PCs. See [INSTALLER_GUIDE.md](../m12c/INSTALLER_GUIDE.md#windows-code-signing-smart-app-control--smartscreen).

**Unsigned builds (temporary):** Right-click the installer → **Properties** → **Unblock**, or use **More info** → **Run anyway** on first launch. Disable Smart App Control on store PCs only if signing is not yet available.

**Pass:** Application opens to connection / login screen without errors. Production window has **no** File/Edit/View menu bar.

---

## 3. macOS — install DMG

1. Open `WEBSTUDIO Desktop.dmg`.
2. Drag **WEBSTUDIO Desktop** to **Applications** (not `webstudio_ims` — that is the Flutter mobile build).
3. First launch: right-click → **Open** if Gatekeeper blocks unsigned builds (sign with `CSC_LINK` for production).
4. Universal binary supports **Intel and Apple Silicon**.

**Pass:** App launches from Applications folder and shows the blue WEBSTUDIO splash or connection screen.

**Blank window on macOS only:** Older DMGs loaded the UI via `file://`, which macOS Chromium blocks for ES module scripts. Rebuild with v1.0.2+ (uses `app://` protocol). Client log: `~/Library/Application Support/WEBSTUDIO Desktop/webstudio-client.log` (packaged) or `~/Library/Application Support/@webstudio/desktop/` (dev).

---

## 4. Discover server

On first launch the desktop client:

1. Browses mDNS for `_webstudio-ims._tcp.local.`
2. Tries configured discovery candidate URLs
3. Falls back to **Manual server URL** if discovery fails

| Method | When |
|--------|------|
| mDNS | Same subnet, UDP 5353 allowed |
| Saved URL | Returning users |
| Manual | `http://<server-ip>:8000` |

**Test:** Server appears in connection list or manual URL connects.

---

## 5. Connect automatically

After first successful connection:

- URL saved in `SavedServerStore` (encrypted local storage)
- `ConnectionReconnectService` polls every **15s** when disconnected
- Hostname resolution supports DHCP mobility on Tally/billing patterns

**Validation:** Restart WEBSTUDIO Server service; desktop reconnects within ~30s without user action.

---

## 6. Authenticate

1. Complete server setup wizard (M14A) before staff login.
2. Enter username and password issued by Main Admin.
3. JWT access + refresh tokens stored locally (`AuthTokenStore`).
4. Session timeout per server security policy.

**API:** `POST /api/v1/auth/login`  
**Gate:** `GET /api/v1/setup/status` must show `system_initialized: true`.

---

## 7. Verify permissions

After login:

| Check | How |
|-------|-----|
| Navigation | Only permitted modules visible in sidebar |
| Restricted pages | Direct URL blocked if missing permission |
| Role label | Shown in user menu |
| Export / admin | Visible only with `*:export` or admin permissions |

Permissions loaded from `GET /api/v1/auth/me` into session; enforced by `permissionArchitecture.ts` and route guards.

**Test users:** Create one **Sales** and one **Main Admin** account; confirm different menus.

---

## 8. Updates

Desktop checks WEBSTUDIO Server for updates:

```http
GET /api/v1/client-updates/check?platform=desktop_windows&current_version=...
GET /api/v1/client-updates/check?platform=desktop_macos&current_version=...
```

Deployment Center distributes approved releases (M13).

---

## 9. Production validation

```http
GET /api/v1/deployment/client-validation
```

Requires network administrator permission. Review `desktop_*` checks.

---

## 10. Troubleshooting

| Symptom | Fix |
|---------|-----|
| Cannot find server | Manual URL; check M14B firewall |
| Login blocked | Complete setup wizard on server |
| Permission denied | Main Admin assigns role |
| Stale session | Log out and in; check server clock |

---

## 11. Sign-off

Complete desktop sections of [CLIENT_ACCEPTANCE_CHECKLIST.md](CLIENT_ACCEPTANCE_CHECKLIST.md) (CLI-01–CLI-05).
