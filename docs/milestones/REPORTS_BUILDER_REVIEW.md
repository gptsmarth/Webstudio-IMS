# Reports & Export Center — Report Builder Review

## Summary

The Reports page is now a **Report Builder** workflow:

1. Select report type (Inventory, Sales, Audit, Tally)
2. Configure combinable filters
3. **Preview results** (paginated table, sortable columns, sticky header)
4. Export Excel/PDF using the **same filters** (CSV placeholder disabled)

Static per-section download buttons (By Brand, By Location, All Inventory, Brand-wise Sales, etc.) were removed.

## Desktop

- `ReportsPage.tsx` — builder layout
- `hooks/useReportBuilder.ts` — state, preview, export orchestration
- `components/reports/*` — type selector, filters, preview table, export bar, saved-reports placeholder
- `services/api/ReportService.ts` — typed preview + filtered export
- `types/savedReports.ts` — future saved/favourite/recent architecture (not persisted)
- `lib/reportDatePresets.ts` — sales/audit/tally date presets

## Backend

- Extended `ReportFilters` and `/api/v1/reports/*` query params (serial, color, archived, purchase dates, location type, sales dimensions, audit action/source/role, tally notification filters, sorting)
- Export endpoint accepts the same filter surface (inventory, sales, audit, notification only — aggregate location/brand/model export buttons removed from UI)

## Screenshots

Capture manually per `docs/milestones/screenshots/README.md`:

- Light mode: Reports builder with inventory preview visible
- Dark mode: same state

## Verification

```bash
pnpm --filter @webstudio/desktop typecheck
pnpm --filter @webstudio/desktop test
pytest apps/backend/tests/reports/
```

Stop for review.
