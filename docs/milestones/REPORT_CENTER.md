# Professional Report Center

**Status:** Ready for review  
**Scope:** Desktop Report Center UI (replaces prior Reports page layout)

## Workflow

```
Choose Report Type → Configure Filters → Preview Results → Export
```

Export is **disabled until preview runs**. Exports use the same filter set as the preview table.

## Report types

| Type | Filters |
|------|---------|
| **Inventory** | Store, Location, Brand, Product Model, Serial, Status (Available / Sold / Archived), Created date + range, Color, Search |
| **Sales** | Date presets + custom range, Store, Location, Brand, Product Model, Serial, Invoice, Customer, Salesperson, Payment mode, Sale source, Search |
| **Audit** | User, Role, Operation, Date range, Serial, Location, Action source, Search |
| **Tally** | Company, Date range, Sync status, Invoice, Outcome (Processed / Skipped / Duplicate / Missing serial / Missing model / Model mismatch), Notification type, Search |

Switching report type resets filters and clears preview.

## Preview

- Sortable columns
- Pagination (50 rows per page)
- Sticky table header
- Row count in preview header
- Empty state until preview is run

## Export

- Excel (`.xlsx`)
- PDF
- CSV button present (architecture ready; not yet enabled)

## Removed / excluded

- **Warranty** — no filters, reports, exports, or APIs
- Saved reports sidebar (placeholder removed from page)

## New modules

| File | Role |
|------|------|
| `lib/reportBuilder.ts` | Filter types + query param builder |
| `components/reports/filters/*` | Per-report-type filter panels |
| `components/reports/ReportWorkflowSteps.tsx` | Workflow step indicator |
| `pages/workspace/ReportsPage.tsx` | Report Center layout |

## Screenshots (manual)

| File | Capture |
|------|---------|
| `60-report-center-inventory-light.png` | Inventory report — filters + preview |
| `61-report-center-sales-light.png` | Sales report type selected |
| `62-report-center-preview-light.png` | Preview table with row count |
| `63-report-center-export-light.png` | Export bar enabled after preview |

## Verification

```bash
pnpm typecheck
pnpm lint
cd apps/desktop && pnpm test && pnpm build
```
