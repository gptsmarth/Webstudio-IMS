---
Title: iOS Guide — WEBSTUDIO IMS
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12H
---

# iOS Guide

**WEBSTUDIO IMS** for iPhone and iPad. Distribution requires Apple signing (M12C).

---

## 1. Requirements

| Item | Detail |
|------|--------|
| iOS | 15.5 or newer |
| Network | Same LAN as server |
| Distribution | TestFlight, Ad Hoc IPA, or Enterprise (when configured) |

**Bundle ID:** `com.webstudio.webstudioIms`

---

## 2. Build (IT)

```bash
WEBSTUDIO_IOS_EXPORT_OPTIONS_PLIST=/absolute/path/to/ExportOptions.plist \
  bash scripts/release/build-ios-ipa.sh
```

Requires Xcode, an Apple signing identity, and a provisioning profile.
CI keeps an unsigned archive for compile validation. Follow the
[TestFlight setup](../m12c/INSTALLER_GUIDE.md#set-up-testflight-on-a-mac) to
install a signed build for a pilot.

---

## 3. Installation options

| Method | Audience |
|--------|----------|
| **TestFlight** | Pilot users (recommended) |
| **Ad Hoc IPA** | Registered device UDIDs |
| **Enterprise** | Internal MDM |

---

## 4. First launch

1. Open **WEBSTUDIO IMS**
2. Allow local network access when prompted (iOS 14+)
3. Enter the office server's trusted HTTPS address or select it from local discovery
4. Log in

---

## 5. Features

Same core modules as Android:

- Dashboard, Inventory, Sales, Tally status, Settings
- Mandatory update gate vs server `min_mobile_version`

---

## 6. Local network privacy

iOS may block discovery until user grants **Local Network** permission. If server not found:

1. Settings → WEBSTUDIO IMS → Local Network → On
2. Or enter server URL manually

---

## 7. Updates

Install new build via TestFlight or MDM push. Match server minimum version after server upgrades.

---

## 8. Troubleshooting

| Issue | Action |
|-------|--------|
| Signing or provisioning error | Confirm the build is installed through its configured TestFlight, Ad Hoc, or MDM distribution channel |
| Cannot connect | Local Network permission; verify LAN |
| App won't open | Reinstall; check iOS version |

[Troubleshooting Guide](TROUBLESHOOTING_GUIDE.md)
