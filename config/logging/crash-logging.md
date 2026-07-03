---
Title: Crash Logging Configuration
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12G
---

# Crash Logging

## Backend

| Mechanism | Path / behaviour |
|-----------|------------------|
| Uncaught exceptions | Loguru ERROR with stack trace → stdout + `WEBSTUDIO_LOG_DIR` |
| Dedicated crash file | `WEBSTUDIO_CRASH_LOG_DIR/webstudio-crash.log` (ERROR+ only) |
| Graceful shutdown | `shutdown_orchestrator` logs checkpoint steps |

Set both directories on production servers:

```
WEBSTUDIO_LOG_DIR=D:\WEBSTUDIO-IMS\logs
WEBSTUDIO_CRASH_LOG_DIR=D:\WEBSTUDIO-IMS\logs\crash
```

## Desktop (Electron)

| Mechanism | Path |
|-----------|------|
| `crashReporter` | Submits to local folder `{userData}/crash-reports/` |
| `uncaughtException` | Appended to `webstudio-client.log` |
| `unhandledRejection` | Appended to `webstudio-client.log` |

Support bundle for LAN offices:

1. `webstudio-client.log`
2. `crash-reports/` folder (if present)
3. Server `webstudio-api.log` and `webstudio-crash.log`

## Mobile

No persistent crash reporter in MVP. Mandatory update gate prevents known-bad client versions.

## Operator escalation

Include printed invoice numbers and sync timestamps — not raw Tally GUIDs — when reporting production issues.
