---
Title: Tally Validation Report
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14C
Related Documents:
  - docs/milestones/m14/TALLY_PRODUCTION_GUIDE.md
  - docs/milestones/m14/TALLY_VALIDATION_CHECKLIST.md
  - docs/milestones/m14/XML_VERIFICATION_GUIDE.md
---

# Tally Validation Report (M14C)

## Executive Summary

Milestone **14C** delivers **production validation for Tally ERP 9 integration**. Validation extends the existing Tally sync engine (M12) with a commissioning API, Windows script, and operator documentation — **no new business features or UI redesign**.

**Assumption:** Live Tally is available on the billing PC after deployment.

| Deliverable | Path |
|-------------|------|
| Tally Production Guide | [TALLY_PRODUCTION_GUIDE.md](TALLY_PRODUCTION_GUIDE.md) |
| Tally Validation Checklist | [TALLY_VALIDATION_CHECKLIST.md](TALLY_VALIDATION_CHECKLIST.md) |
| XML Verification Guide | [XML_VERIFICATION_GUIDE.md](XML_VERIFICATION_GUIDE.md) |

**Verdict:** Production Tally validation is **implemented and test-covered**.

---

## Validation matrix

| Requirement | Check key | Implementation |
|-------------|-----------|----------------|
| XML request generation | `xml_request_generation` | `TallyXmlClient._export_request` template validation |
| Incremental synchronization | `incremental_synchronization` | `resolve_incremental_from_date` + company sync state |
| GUID checkpoint | `guid_checkpoint` | `tally_company_sync.last_processed_guid` |
| Last synchronization timestamp | `last_synchronization_timestamp` | `last_successful_sync_at` |
| Recovery after server restart | `recovery_after_server_restart` | `tally_sync` scheduler + `checkpoint_tally_sync` |
| Recovery after Tally restart | `recovery_after_tally_restart` | `tally_connectivity_probe` scheduler |
| Offline XML replay | `offline_xml_replay` | Offline history status + incremental window |
| Duplicate prevention | `duplicate_prevention` | `TallyProcessedInvoiceRepository.find_by_guid` |
| Manual synchronization | `manual_synchronization` | `POST /sync/trigger` |
| Automatic scheduler | `automatic_scheduler` | `WEBSTUDIO_TALLY_SCHEDULER` + runtime state |
| Configurable polling interval | `configurable_polling_interval` | `tally_sync_interval_seconds` (60–3600) |
| Dashboard synchronization status | `dashboard_synchronization_status` | `TallyDashboardService` operational fields |
| Live Tally (commissioning) | `live_tally_connectivity` | `TallyConnectivityService.test_connection` |

---

## API surface

```http
GET /api/v1/integrations/tally/production-validation
```

Requires `tally:view_status`. Returns validation checks, checklist items, dashboard operational snapshot, and script paths.

Existing endpoints used during commissioning:

| Endpoint | Purpose |
|----------|---------|
| `POST /connection/test` | Live workstation probe |
| `POST /sync/trigger` | Manual sync |
| `GET /dashboard` | Staff-visible sync status |
| `GET /status` | Health summary |
| `GET /sync/history` | Run evidence |

---

## Code references

| Component | Path |
|-----------|------|
| Production validation | `services/tally_production_validation_service.py` |
| Sync engine | `services/tally_sync_service.py` |
| XML client | `integrations/tally/xml_client.py` |
| Incremental helpers | `integrations/tally/incremental_sync.py` |
| Dashboard status | `services/tally_dashboard_service.py` |
| Server restart checkpoint | `services/shutdown_orchestrator.py` |
| Tally probe scheduler | `services/tally_connectivity_scheduler.py` |
| API router | `api/routers/tally.py` |
| Unit tests | `tests/tally/test_tally_production_validation.py` |
| XML analysis tool | `tools/scripts/uat_analyze_tally_xml.py` |
| Windows script | `infra/windows/validate-production-tally.ps1` |

---

## Commissioning sequence

1. Configure Settings → Tally (enable, hostname, port, company, interval).
2. Set `WEBSTUDIO_TALLY_SCHEDULER=1` and `WEBSTUDIO_TALLY_CONNECTIVITY_PROBE=1`.
3. Run **Test Connection** with Tally open.
4. `GET /production-validation` — resolve warnings.
5. Trigger manual sync; verify dashboard **Last Sync** and history.
6. Complete [TALLY_VALIDATION_CHECKLIST.md](TALLY_VALIDATION_CHECKLIST.md) including restart and duplicate tests.
7. Verify XML sample per [XML_VERIFICATION_GUIDE.md](XML_VERIFICATION_GUIDE.md).

---

## Test evidence

```
pytest apps/backend/tests/tally/test_tally_production_validation.py — 2 passed
```

---

## Sign-off

| Criterion | Status |
|-----------|--------|
| All 12 validation checks implemented | ✅ |
| Live Tally connectivity check (commissioning) | ✅ |
| Tally Production Guide published | ✅ |
| Tally Validation Checklist published | ✅ |
| XML Verification Guide published | ✅ |
| Windows validation script | ✅ |
| Unit tests passing | ✅ |

**M14C complete. STOP.**
