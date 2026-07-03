---
Title: Deployment Issues — M12J Simulation
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12J
---

# Deployment Issues

Issues discovered during Milestone 12J customer installation simulation.

---

## Fixed during M12J

| ID | Severity | Component | Issue | Root cause | Fix |
|----|----------|-----------|-------|------------|-----|
| **M12J-001** | High | Tally sync | Background sync crashed on unreachable workstation | `logger.warning(..., extra={"message": ...})` conflicts with stdlib `LogRecord.message` | Renamed extra key to `user_message` in `tally_connectivity_service.py` |
| **M12J-002** | Low | Simulation test | Setup status assertion used wrong field | API returns `system_initialized` not `initialized` | Updated simulation test |
| **M12J-003** | Low | Simulation test | Report payload assertion | Reports use `rows` not `items` | Updated simulation test |

---

## Open — staging drill required

| ID | Severity | Component | Issue | Recommended action |
|----|----------|-----------|-------|-------------------|
| **M12J-004** | Medium | Tally | First sync with live Lenovo not exercised in CI | Run connection test + sync on staging LAN with Tally Prime open |
| **M12J-005** | Medium | Windows | Service auto-start after reboot not live-tested | Reboot server PC; verify `sc query` + health endpoint |
| **M12J-006** | Medium | Mobile | No physical Android/iPhone install in simulation | Sideload APK/IPA; verify camera barcode on device |
| **M12J-007** | Low | Desktop | Electron installer UI not clicked in simulation | Run `WEBSTUDIO Desktop Setup.exe` on staging PC |
| **M12J-008** | Low | Signing | Unsigned installers may trigger SmartScreen | Configure code signing before customer delivery |

---

## Deferred from M12I (unchanged)

See [KNOWN_ISSUES.md](../m12i/KNOWN_ISSUES.md) for MOB-001 (device E2E), REL-02 (signing), BACK-009 (health ready Alembic check), and other accepted post-GA items.

---

## Issue statistics

| Category | Count |
|----------|-------|
| Fixed in M12J | 3 |
| Open (staging) | 5 |
| Critical blockers | **0** |

---

## Impact assessment

**M12J-001** would have caused production error logs (or silent background task failures) whenever Tally workstation was offline during a manual sync — a common business-hours scenario. Fix is included in RC `0.1.0`.

No data-loss or security vulnerabilities identified during simulation.
