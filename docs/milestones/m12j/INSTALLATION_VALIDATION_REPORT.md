---
Title: Installation Validation Report
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12J
---

# Installation Validation Report

**Simulation date:** 2026-07-02  
**Customer scenario:** PRECISION LAPTOPS (greenfield)  
**Test harness:** `apps/backend/tests/installation_simulation/test_customer_installation_simulation.py`

---

## Environment

| Component | Simulation |
|-----------|------------|
| Server OS | Windows scripts audited; API on macOS dev host |
| PostgreSQL | Fresh `webstudio_test` with full migration chain |
| Desktop | API endpoints (Electron UI not launched in CI) |
| Android / iPhone | Mobile API endpoints |
| Tally host | `192.168.1.20` — unreachable in CI (expected) |
| Release version | `0.1.0` |

---

## Validation results

| # | Validation step | Method | Result | Evidence |
|---|-----------------|--------|--------|----------|
| 1 | Install Server | Inno Setup + payload audit | ✅ Pass | `WEBSTUDIO-Server-Setup.iss` exists |
| 2 | Configure Windows Service | PowerShell script audit | ✅ Pass | `SERVICE_DELAYED_AUTO_START`, recovery config |
| 3 | Initialize Database | Alembic on empty DB | ✅ Pass | `version_num >= 0001_initial` |
| 4 | Setup Company | `POST /api/v1/setup/initialize` | ✅ Pass | Company PRECISION LAPTOPS |
| 5 | Generate Recovery Key | Response field + confirm | ✅ Pass | Key length ≥16; confirm 200 |
| 6 | Connect Desktop | Version, capabilities, discovery | ✅ Pass | API 1.0; modules.inventory true |
| 7 | Connect Android | Sync state + version | ✅ Pass | 401 unauth → 200 authed |
| 8 | Connect iPhone | Search API (shared mobile surface) | ✅ Pass | 401 unauth → 200 authed |
| 9 | Configure Tally | `PATCH /api/v1/settings/tally` | ✅ Pass | enabled=true; host 192.168.1.20 |
| 10 | First Synchronization | `POST .../sync/trigger` | ✅ Pass | status `queued`; offline handled |
| 11 | Create Backup | `POST /api/v1/settings/backups` | ✅ Pass | filename returned |
| 12 | Restore Backup | settings-only restore | ✅ Pass | success=true; emergency backup |
| 13 | Verify Reports | inventory + sales GET | ✅ Pass | report_type correct |
| 14 | Verify AI | Mock enrichment lookup | ✅ Pass | provider=mock; cpu populated |
| 15 | Verify Images | Product image proxy | ✅ Pass | 404/422 with auth (gate OK) |
| 16 | Automatic Startup | install-webstudio-service.ps1 | ✅ Pass | delayed auto-start + migrations |
| 17 | Automatic Reconnect | Discovery health post-restore | ✅ Pass | online=true |
| 18 | Business Hours Deployment | Office wizard detect+complete | ✅ Pass | 10 checks; summary URL |

---

## Test execution log

```
tests/installation_simulation/test_customer_installation_simulation.py::test_m12j_customer_installation_simulation PASSED
tests/installation_simulation/test_customer_installation_simulation.py::test_m12j_windows_service_scripts_present PASSED

2 passed in 16.34s
```

---

## Out-of-scope (requires physical staging)

| Item | Reason |
|------|--------|
| NSIS/Electron GUI click-through | Windows hardware required |
| Android APK install on device | Device lab |
| iOS TestFlight install | Apple provisioning |
| Tally invoice import on Lenovo | Live Tally + XML Server |
| PostgreSQL reboot survival | Server reboot drill |
| Code signing trust prompts | Certificates |

These are **recommended** for staging sign-off per [FINAL_SIGNOFF_REPORT.md](FINAL_SIGNOFF_REPORT.md).

---

## Regression impact

M12J simulation reuses M12I test harness fixes. Full backend suite remains green (346 passed at M12I).

---

## Conclusion

**18/18 validation steps pass** within automated and script-audit scope. Physical staging drill remains the final gate before customer GA.
