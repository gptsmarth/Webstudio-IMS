---
Title: Desktop Guide — WEBSTUDIO IMS
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12H
---

# Desktop Guide

**WEBSTUDIO Desktop** — primary client for Windows and macOS showrooms.

---

## 1. System requirements

| | Windows | macOS |
|---|---------|-------|
| OS | Windows 10/11 | macOS 12+ |
| RAM | 4 GB | 4 GB |
| Network | Same LAN as server | Same LAN as server |
| Disk | 500 MB | 500 MB |

---

## 2. Installation

See [Installation Guide](INSTALLATION_GUIDE.md) §5–6.

---

## 3. Connecting to server

### Automatic discovery

1. Launch app — **Searching for servers** on Connection page
2. Select discovered server or wait for saved server

### Manual connection

1. Enter `http://{server-ip}:8000`
2. **Test connection** → Save

Connection status in toolbar: **Online** / **Offline** (auto-reconnect every 15s).

---

## 4. Login and session

- Username + password from administrator
- Session timeout per security settings (default 15 min idle logout)
- **Remember me** if enabled by policy

---

## 5. Main features

| Module | Use |
|--------|-----|
| Dashboard | KPIs, recent activity |
| Inventory | Search, add, transfer, archive |
| Sales | Sale history and detail |
| Catalogue | Brands, models, locations |
| Reports | Export inventory/sales |
| Notifications | System alerts |
| Settings | Admin configuration |

---

## 6. Keyboard shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+K (Cmd+K) | Global search |
| Esc | Close modal / drawer |

---

## 7. Logs (support)

Client log file:

- Windows: `%APPDATA%\WEBSTUDIO Desktop\webstudio-client.log`
- macOS: `~/Library/Application Support/WEBSTUDIO Desktop/webstudio-client.log`

Crash reports: `crash-reports/` in same userData folder.

Provide to IT with server logs when reporting issues.

---

## 8. Updates

1. Administrator distributes new `WEBSTUDIO Desktop Setup.exe` / `.dmg`
2. Run installer over existing install
3. Reconnect to server — no data loss on client

Check **minimum version** gate if server was upgraded first.

---

## 9. Troubleshooting

| Issue | Fix |
|-------|-----|
| Cannot find server | Manual URL; check Wi‑Fi |
| Login failed | Verify caps; ask admin |
| Blank after update | Clear saved URL; reconnect |

[Troubleshooting Guide](TROUBLESHOOTING_GUIDE.md)
