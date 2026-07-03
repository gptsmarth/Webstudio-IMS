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
| iOS | 14.0 or newer |
| Network | Same LAN as server |
| Distribution | TestFlight, Ad Hoc IPA, or Enterprise (when configured) |

**Bundle ID:** `com.webstudio.webstudio_ims`

---

## 2. Build (IT)

```bash
bash scripts/release/build-ios-ipa.sh
```

Requires Xcode, signing certificates, `ExportOptions.plist`. CI iOS job disabled until secrets configured — see [M12C Installer Guide](../m12c/INSTALLER_GUIDE.md).

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
3. Discover server or enter `http://{server-ip}:8000`
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
| Untrusted developer | Settings → General → VPN & Device Management → Trust |
| Cannot connect | Local Network permission; verify LAN |
| App won't open | Reinstall; check iOS version |

[Troubleshooting Guide](TROUBLESHOOTING_GUIDE.md)
