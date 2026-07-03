---
Title: Network Validation Report
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14B
Related Documents:
  - docs/milestones/m14/INFRASTRUCTURE_CHECKLIST.md
  - docs/milestones/m14/FIREWALL_CONFIGURATION_GUIDE.md
  - docs/milestones/m12h/NETWORKING_GUIDE.md
---

# Network Validation Report (M14B)

## Executive Summary

Milestone **14B** implements **production networking validation** for WEBSTUDIO IMS on the store LAN. Validation extends the existing M12D network administrator wizard with a **production scope** covering static IP documentation, LAN reachability, multi-AP Wi‑Fi guidance, client platform endpoints, firewall posture, PostgreSQL locality, discovery, and automatic reconnect readiness.

| Deliverable | Path |
|-------------|------|
| Network Validation Report | This document |
| Infrastructure Checklist | [INFRASTRUCTURE_CHECKLIST.md](INFRASTRUCTURE_CHECKLIST.md) |
| Firewall Configuration Guide | [FIREWALL_CONFIGURATION_GUIDE.md](FIREWALL_CONFIGURATION_GUIDE.md) |

**Verdict:** Production networking validation is **implemented and test-covered**. Operators run validation on the server after M14A install and firewall configuration.

---

## Validation matrix

| Requirement | Check key | Implementation | Operator action |
|-------------|-----------|----------------|-----------------|
| Static server IP | `static_server_ip` | LAN IP vs `office_discovery_urls` / `WEBSTUDIO_DISCOVERY_CANDIDATES` | Document IP in Office Deployment |
| LAN accessibility | `lan_accessibility` | Socket + HTTP probe on LAN base URL | Fix bind host / firewall |
| Multiple Wi‑Fi access points | `multi_wifi_access_points` | Discovery candidates + multi-SSID guidance | Same VLAN; disable AP isolation |
| Same subnet communication | `same_subnet_communication` | Bind host + subnet hint (`/24`) | Router config review |
| Desktop connectivity | `desktop_connectivity` | `/api/v1/health/live` on LAN | On-device Connection diagnostics |
| Android connectivity | `android_connectivity` | HTTP probe `/client-updates/check?platform=mobile_android` | Test app on store Wi‑Fi |
| iOS connectivity | `ios_connectivity` | HTTP probe `/client-updates/check?platform=mobile_ios` | Test app on store Wi‑Fi |
| Windows Firewall | `windows_firewall` | Localhost vs LAN socket probe | `configure-firewall.ps1` |
| Port availability | `port_availability` | API 8000, PG 5432 localhost, mDNS 5353 | Service + firewall |
| PostgreSQL connectivity | `postgresql_connectivity` | `verify_postgresql` + migration head | PG service on server |
| API reachability | `api_reachability` | Local + LAN HTTP `/health/live` | WEBSTUDIO Server service |
| Server discovery | `server_discovery` | mDNS state + `build_discovery_health_payload` | Enable mDNS or candidate URLs |
| Automatic reconnect | `automatic_reconnect` | Discovery health + candidate URLs | Restart test on clients |

---

## API surface (extended, not redesigned)

Existing network admin endpoints accept `scope=production`:

```http
POST /api/v1/network/admin/validate?scope=production
GET  /api/v1/network/admin/report?scope=production
```

Standard scope (`scope=standard`, default) retains M12D wizard checks (server, database, API, Tally, AI, backup folders).

**Response additions (production report):**

| Field | Purpose |
|-------|---------|
| `validation_scope` | `"production"` |
| `infrastructure_checklist` | NET-01…NET-10 items for sign-off |
| `api_bind_host` | Confirms `0.0.0.0` LAN bind |
| `firewall_script` | `infra/windows/configure-firewall.ps1` |
| `validation_script` | `infra/windows/validate-production-network.ps1` |

---

## Code references

| Component | Path |
|-----------|------|
| Production validation service | `apps/backend/src/webstudio_backend/services/network_validation_service.py` |
| Network admin API | `apps/backend/src/webstudio_backend/api/routers/network.py` |
| API schemas | `apps/backend/src/webstudio_backend/api/schemas/network.py` |
| Unit tests | `apps/backend/tests/network/test_network_validation.py` |
| Firewall script | `infra/windows/configure-firewall.ps1` |
| Server validation script | `infra/windows/validate-production-network.ps1` |
| Desktop auto-reconnect | `apps/desktop/src/services/ConnectionReconnectService.ts` |
| Discovery health | `apps/backend/src/webstudio_backend/services/discovery_health_service.py` |
| Desktop network wizard UI | `apps/desktop/src/components/settings/NetworkAdminWizard.tsx` |

---

## Windows server validation sequence

1. Complete M14A installation and start **WEBSTUDIO Server** service.
2. Run `configure-firewall.ps1` — see [FIREWALL_CONFIGURATION_GUIDE.md](FIREWALL_CONFIGURATION_GUIDE.md).
3. Run `validate-production-network.ps1` (elevated).
4. From desktop (Network Admin): `POST …/validate?scope=production`.
5. Complete [INFRASTRUCTURE_CHECKLIST.md](INFRASTRUCTURE_CHECKLIST.md) on-device tests (desktop, Android, iOS).
6. Restart server; confirm clients auto-reconnect (NET-10).

---

## Test evidence

```
pytest apps/backend/tests/network/test_network_validation.py — 4 passed
```

Tests assert:

- Standard wizard retains core M12D check keys.
- Production scope includes all 13 M14B check keys.
- Production report exposes infrastructure checklist and script paths.

---

## Known limitations

| Limitation | Mitigation |
|------------|------------|
| Server cannot fully simulate mobile/desktop UI | On-device checklist items CLI-01…CLI-04 |
| HTTP probes require running API on target port | Run validation with service up |
| Static IP detection is documentary | DHCP reservation + Office Deployment URLs |
| mDNS UDP probe is best-effort | Rely on mDNS service state + discovery health |

---

## Sign-off

| Criterion | Status |
|-----------|--------|
| All 13 validation checks implemented | ✅ |
| Infrastructure checklist published | ✅ |
| Firewall guide published | ✅ |
| API `scope=production` on existing endpoints | ✅ |
| Windows PowerShell validation script | ✅ |
| Unit tests passing | ✅ |

**M14B complete. STOP.**
