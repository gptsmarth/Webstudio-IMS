---
Title: Production Logging Configuration
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12G
---

# Production Logging

## Backend (WEBSTUDIO Server)

| Variable | Production value |
|----------|------------------|
| `APP_ENV` | `production` |
| `LOG_LEVEL` | `INFO` (use `DEBUG` only during support windows) |
| `LOG_JSON` | `true` (auto-enabled when `APP_ENV=production`) |
| `WEBSTUDIO_LOG_DIR` | e.g. `D:\WEBSTUDIO-IMS\logs` |

When `WEBSTUDIO_LOG_DIR` is set, the API writes:

| File | Content |
|------|---------|
| `webstudio-api.log` | Rotating application log (10 MB × 5 files) |
| JSON lines when `LOG_JSON=true` | Suitable for log agents |

NSSM also captures stdout/stderr per [WINDOWS_SERVICE_GUIDE.md](../../docs/milestones/m12b/WINDOWS_SERVICE_GUIDE.md).

### Sample JSON line

```json
{"timestamp":"2026-07-02T12:00:00+00:00","level":"INFO","message":"http_request","module":"request_logging","function":"dispatch","line":40,"extra":{}}
```

## Desktop (Electron)

| Location | `{userData}/webstudio-client.log` |
| Level | INFO in production builds |
| Crashes | `{userData}/crash-reports/` when crashReporter enabled |

## Mobile (Flutter)

Release builds: framework errors only unless user exports diagnostics. Server-side correlation via audit logs and API request IDs.

## Log rotation (host)

Use `logrotate-webstudio.conf.example` on Linux or Windows Task Scheduler + PowerShell to archive logs older than 30 days.

## Security

Never log JWT tokens, passwords, Tally credentials, or full payment data.
