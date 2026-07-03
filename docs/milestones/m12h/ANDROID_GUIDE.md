---
Title: Android Guide — WEBSTUDIO IMS
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12H
---

# Android Guide

**WEBSTUDIO IMS** mobile app for Android showrooms (APK distribution).

---

## 1. Requirements

| Item | Detail |
|------|--------|
| Android | 8.0 (API 26) or newer |
| Network | Same Wi‑Fi/LAN as server |
| APK | `WEBSTUDIO IMS.apk` from release bundle |

---

## 2. Installation

1. Copy APK to device (USB, email link, or MDM)
2. Settings → Security → allow install from unknown sources (if sideloading)
3. Open APK → Install
4. Launch **WEBSTUDIO IMS**

**Bundle ID:** `com.webstudio.webstudio_ims`

---

## 3. First launch

1. **Connection** screen — app searches LAN or prompts for URL
2. Enter `http://{server-ip}:8000` if discovery fails
3. **Login** with staff credentials

Server URL saved in device storage for reconnect.

---

## 4. Features

| Screen | Capability |
|--------|------------|
| Dashboard | Summary metrics |
| Inventory | Browse, search, detail |
| Sales | List and detail |
| More / Settings | Tally status, connection |
| Notifications | Alerts (role-based) |

Feature parity with desktop is documented in mobile milestone reports.

---

## 5. Mandatory update

If server requires newer client:

- App shows update gate with minimum version
- Install new APK from administrator
- Reopen app

---

## 6. Offline behaviour

- Cached data limited — live server required for writes
- Reconnect automatically when app returns to foreground (lifecycle observer)

---

## 7. Permissions

| Permission | Why |
|------------|-----|
| Internet / Network | API communication |
| Camera (optional) | QR scan if enabled |

---

## 8. Troubleshooting

| Issue | Action |
|-------|--------|
| Server not found | Same Wi‑Fi as server; enter IP manually |
| Login error | Check username; server online |
| Update required | Install latest APK |

[Troubleshooting Guide](TROUBLESHOOTING_GUIDE.md)

---

## 9. Uninstall

Settings → Apps → WEBSTUDIO IMS → Uninstall

Local tokens cleared; server data unaffected.
