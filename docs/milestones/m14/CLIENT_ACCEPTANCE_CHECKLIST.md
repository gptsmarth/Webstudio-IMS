---
Title: Client Acceptance Checklist — Production
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14E
Related Documents:
  - docs/milestones/m14/DESKTOP_DEPLOYMENT_GUIDE.md
  - docs/milestones/m14/MOBILE_DEPLOYMENT_GUIDE.md
  - docs/milestones/m14/CLIENT_DEPLOYMENT_REPORT.md
---

# Client Acceptance Checklist (M14E)

Sign-off checklist for **desktop and mobile client deployment** on production (or staging mirror).

Mark **Pass / Fail / N/A**. Attach screenshots or photos as evidence.

---

## A. Prerequisites

| ID | Check | Pass criteria | Evidence |
|----|-------|---------------|----------|
| PRE-01 | Server commissioned | M14A complete; `/health/ready` OK | Health screenshot |
| PRE-02 | Networking | M14B LAN validation passed | Network report |
| PRE-03 | Staff accounts | Users created with correct roles | User list |
| PRE-04 | Release artifacts | EXE, DMG, APK (and iOS IPA if used) from server catalog | Filenames + versions |

---

## B. Desktop — Windows EXE

| ID | Check | Pass criteria | Evidence |
|----|-------|---------------|----------|
| CLI-01 | Install EXE | Setup completes; shortcuts created | Install screenshot |
| CLI-02 | Launch | App opens without error | Screenshot |
| CLI-03 | Discover server | mDNS or manual URL connects | Connection screen |
| CLI-04 | Auto-reconnect | Reconnects after server service restart | Notes + timestamp |
| CLI-05 | Login | Staff user authenticates | Login success |
| CLI-06 | Permissions | Menu matches role; restricted routes blocked | Two-role comparison |

---

## C. Desktop — macOS DMG

| ID | Check | Pass criteria | Evidence |
|----|-------|---------------|----------|
| CLI-07 | Install DMG | App in Applications | Screenshot |
| CLI-08 | Launch | Opens on target Mac (Intel or Apple Silicon) | Screenshot |
| CLI-09 | Connect + login | Same as Windows CLI-03–06 | Screenshots |

---

## D. Flutter — Android APK

| ID | Check | Pass criteria | Evidence |
|----|-------|---------------|----------|
| CLI-10 | Install APK | Sideload succeeds on store device | App drawer |
| CLI-11 | Connect | Discovery or manual URL on store Wi‑Fi | Connection screen |
| CLI-12 | Login | Staff credentials work | Screenshot |
| CLI-13 | Restore session | Still logged in after force-close + reopen | Video or notes |
| CLI-14 | Offline drill | Banner + cached lookup after airplane mode | Screenshot |
| CLI-15 | Camera scan | Camera permission; serial scanned | Photo of scan result |
| CLI-16 | Barcode lookup | Known serial opens item detail | Screenshot |

---

## E. iOS

| ID | Check | Pass criteria | Evidence |
|----|-------|---------------|----------|
| CLI-17 | Architecture | arm64 device build; bundle ID correct | Xcode / IPA metadata |
| CLI-18 | Install | TestFlight, Ad Hoc, or MDM install succeeds | Device screenshot |
| CLI-19 | Local network | Permission granted; server found | iOS settings |
| CLI-20 | Connect + login | Same as Android CLI-11–12 | Screenshots |
| CLI-21 | Session restore | App restart retains session (on LAN) | Notes |
| CLI-22 | Camera + barcode | Physical device scan test | Photo |

---

## F. Cross-client

| ID | Check | Pass criteria | Evidence |
|----|-------|---------------|----------|
| CLI-23 | Version check | Clients report version; server accepts min version | About / version screen |
| CLI-24 | Update authority | Clients use server `/client-updates/check` only | Network capture (optional) |
| CLI-25 | Same data | Inventory count consistent across clients | Spot-check serial |

---

## G. Automated server validation

```http
GET /api/v1/deployment/client-validation
```

**Pass:** `overall_status` is `passed` or `warning` with documented remediation.

Required check keys present:

- Desktop: `desktop_install_exe`, `desktop_discover_server`, `desktop_authenticate`, `desktop_verify_permissions`
- Flutter: `flutter_install_apk`, `flutter_connect`, `flutter_restore_session`, `flutter_offline_validation`
- iOS: `ios_installation_architecture`, `ios_validate_installation`

---

## H. Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Store administrator | | | |
| IT | | | |
| WEBSTUDIO engineer | | | |

**Overall result:** ☐ Pass — clients production ready &nbsp; ☐ Fail — remediate before staff rollout

---

## I. Rollout order (recommended)

1. Main Admin desktop (Windows server room or office PC)
2. Floor supervisor desktop
3. Android devices (floor staff)
4. iOS pilot devices
5. Remaining desktops

Do not distribute clients before server setup wizard is complete.
