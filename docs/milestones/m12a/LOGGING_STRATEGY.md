---
Title: Logging Strategy
Version: 1.0.0
Status: Final — Awaiting Review
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12A
---

# Logging Strategy — Production Packaging Audit

**Purpose:** Document current logging behavior and recommend production collection without code changes in M12A.

---

## Design goals

1. **Structured server logs** for aggregation and alerting  
2. **No secrets in logs** — tokens, passwords, Tally credentials redacted  
3. **Correlation** — request ID / user context where available  
4. **Operator-accessible** client logs for LAN support  
5. **Retention** — business-defined; not enforced in application code today  

---

## Backend (FastAPI / Loguru)

### Current implementation

| Aspect | Behavior |
|--------|----------|
| Library | Loguru |
| Output | **stdout only** (container/service friendly) |
| Format | Human-readable dev; **JSON** when `APP_ENV=production` or `LOG_JSON=true` |
| Level | `LOG_LEVEL` env (default INFO) |
| File rotation | **Not implemented in code** |

### JSON fields (production)

Typical structured fields include timestamp, level, message, module, and exception traces. Suitable for:

- Windows Event Log forwarder + file capture  
- systemd journal  
- ELK / Loki / CloudWatch (if cloud-hosted later)  

### What gets logged

| Category | Level | Notes |
|----------|-------|-------|
| HTTP requests | INFO | Path, status, duration |
| Auth failures | WARNING | No password values |
| Tally sync runs | INFO | Company, counts, errors summarized |
| Scheduler ticks | DEBUG/INFO | Enable DEBUG only for support windows |
| DB errors | ERROR | Stack traces |

### Gaps vs architecture docs

DEPLOY-001 references `D:\WEBSTUDIO-IMS\logs\` — **host must configure** log redirection (NSSM stdout redirect, `>> api.log`, or logging agent). Application does not write there directly.

---

## Desktop (Electron)

### Current implementation

| Aspect | Behavior |
|--------|----------|
| Location | `{userData}/webstudio-client.log` |
| Writer | Electron **main** process |
| Renderer | Console → devtools in dev; errors should surface to main where wired |

### Production recommendations

| Practice | Detail |
|----------|--------|
| Support bundle | Operator collects `webstudio-client.log` + server logs |
| Rotation | OS/user responsibility; consider max size in M12+ |
| PII | Avoid logging full JWT or inventory PII at INFO |

---

## Flutter (Mobile)

### Current implementation

| Aspect | Behavior |
|--------|----------|
| Debug | `debugPrint` / Flutter framework logs |
| Release | Minimal unless explicit logging added |
| Persistence | **No** ship-ready log file on device |

### Production recommendations

| Practice | Detail |
|----------|--------|
| MVP | Support via screenshot + server-side correlation |
| M12+ optional | `logger` package + encrypted local file with user export |
| Crash | Consider Firebase Crashlytics / Sentry only if approved in ADR |

---

## Database & audit trail

| Mechanism | Purpose |
|-----------|---------|
| Application tables | Business audit (inventory movements, user actions) — not stdout logs |
| `tally_sync_history` | Operational sync audit |
| PostgreSQL logs | DBA-level — separate from app |

**Distinction:** Application logging ≠ financial audit trail. Both required for enterprise support.

---

## Log levels by environment

| Environment | Backend | Desktop | Mobile |
|-------------|---------|---------|--------|
| Development | DEBUG allowed | Verbose main log | Flutter verbose |
| Staging | INFO | INFO | INFO |
| Production | INFO (DEBUG for incidents) | INFO | WARN+ only |

---

## Security & compliance

| Rule | Implementation |
|------|----------------|
| No credentials in logs | Review Tally/HTTP error messages |
| JWT | Log validation failure, not token string |
| GDPR / local law | Retention policy owned by customer IT |

---

## Production collection architecture (recommended)

```
┌──────────────┐     stdout JSON      ┌─────────────────┐
│ webstudio-api│ ──────────────────► │ NSSM / systemd   │
└──────────────┘                     │ → file or agent  │
                                     └────────┬─────────┘
                                              │
                                     ┌────────▼─────────┐
                                     │ Operator SIEM /    │
                                     │ log search (opt.)  │
                                     └────────────────────┘

┌──────────────┐   webstudio-client.log   Support staff
│ Electron app │ ────────────────────────► manual collect
└──────────────┘
```

---

## M12 packaging actions (post-audit)

| Action | Layer |
|--------|-------|
| Document stdout redirect in server installer readme | Backend |
| Add log path to release checklist smoke test | Ops |
| Verify JSON parse sample in staging | QA |
| Optional: log rotation sidecar | Infra — not app code |

---

## Related documents

- [PRODUCTION_ENVIRONMENT_CONFIGURATION.md](./PRODUCTION_ENVIRONMENT_CONFIGURATION.md)
- [PRODUCTION_PACKAGING_REPORT.md](./PRODUCTION_PACKAGING_REPORT.md)
- SYSTEM_ARCHITECTURE logging section (if present in docs/architecture)
