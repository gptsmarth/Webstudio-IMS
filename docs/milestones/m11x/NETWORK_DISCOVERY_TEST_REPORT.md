---
Title: Network Discovery Test Report
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 11X
---

# Network Discovery Test Report — Milestone 11X

## Scope

Automated coverage for discovery metadata, host validation, saved-server persistence, diagnostics wiring, and LAN advertisement lifecycle.

## Backend Tests

**File:** `apps/backend/tests/test_network_discovery.py`

| Test | Result |
|------|--------|
| `test_normalize_accepts_ipv4` | Pass |
| `test_normalize_accepts_hostname` | Pass |
| `test_normalize_accepts_mdns_local` | Pass |
| `test_normalize_rejects_empty` | Pass |
| `test_discovery_health` | Pass |
| `test_validate_host_endpoint` | Pass |
| `test_validate_host_rejects_invalid` | Pass |
| `test_mdns_service_skipped_in_test_env` | Pass |
| `test_mdns_txt_record_keys` | Pass |

Run:

```bash
cd apps/backend && pytest tests/test_network_discovery.py -q
```

## Desktop Tests

**File:** `apps/desktop/src/services/network-discovery.test.ts`

| Test | Coverage |
|------|----------|
| IPv4 normalization | `normalizeServerHost` |
| Hostname / `.local` | `normalizeServerHost` |
| URL building | `normalizeServerUrl`, `buildServerUrl` |

Run:

```bash
cd apps/desktop && pnpm test
```

## Mobile Tests

| File | Coverage |
|------|----------|
| `test/core/network/host_validation_test.dart` | IPv4, hostname, mDNS, URL normalization |
| `test/features/connection/saved_server_test.dart` | Extended saved server JSON + legacy compat |

Run:

```bash
cd apps/mobile_flutter && flutter test test/core/network/host_validation_test.dart test/features/connection/saved_server_test.dart
```

## Manual / LAN Verification (Recommended)

| Scenario | Platform | Expected |
|----------|----------|----------|
| Backend start advertises service | Linux/macOS/Windows server | `_webstudio-ims._tcp` visible via Bonjour browser |
| Desktop discovers server | Windows/macOS | Server listed with company + version |
| Mobile discovers server | Android/iOS | One-tap Connect |
| Manual IP connect | All | Staged diagnostics all ✓ |
| Hostname DHCP change | Desktop/Mobile | Saved server resolves new IP |
| mDNS disabled | Backend `WEBSTUDIO_MDNS_ENABLED=0` | Manual + saved servers still work |
| Tally sync | Backend | Unaffected; hostname resolution independent |

## Gaps / Follow-Up

- End-to-end mDNS integration test requires multicast-capable CI runner (not run in default pipeline)
- Electron mDNS browser validated via manual LAN test; unit tests cover shared normalization only
- Bonsoir platform channel tests require device/emulator for full browse simulation

## Summary

Core discovery logic, API endpoints, host validation, and client persistence are covered by automated tests. Full multicast discovery is validated manually on a shared LAN before Milestone 12 packaging.
