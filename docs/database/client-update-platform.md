---
Title: Client Update Platform
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Related: M13E, client-updates API
---

# Client Update Platform

Enterprise clients discover and download updates from WEBSTUDIO Server only. GitHub is contacted exclusively by the server (M13B).

## API

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/client-updates/check` | Version comparison + artifact metadata |
| `GET /api/v1/client-updates/download` | Binary artifact streaming |

## Platform modes

| Platform | `distribution_mode` | Install path |
|----------|-------------------|--------------|
| `desktop_windows` | `installer` | EXE via Electron IPC |
| `desktop_macos` | `installer` | DMG open + restart |
| `mobile_android` | `apk_sideload` | APK download + SHA256 + system installer |
| `mobile_ios` | `app_store_notification` | App Store URL only — no IPA |

## Settings synced on deploy

- `mobile_latest_version`, `mobile_apk_download_url`, `mobile_min_supported_version`
- `desktop_latest_version`, `desktop_windows_download_url`, `desktop_min_supported_version`
- `mobile_ios_app_store_url`

## OpenAPI

[docs/api/openapi/client-updates-v1.yaml](../api/openapi/client-updates-v1.yaml)
