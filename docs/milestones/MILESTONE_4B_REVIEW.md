# Milestone 4B — Sales Workspace (Review)

## Summary

The Sales Workspace is a full desktop operations surface for completed sales, structurally aligned with the Inventory Workspace (4A): always-visible filters, sortable/resizable table, keyboard navigation, detail drawer, export, and polished empty states.

## What was built

### Page layout
- **Header** — title and subtitle
- **Toolbar** — debounced search, Export (XLSX, admin only), Refresh
- **Filters panel** — always visible: date range, brand, store, salesperson, invoice, customer, payment mode, sale source
- **Table** — sticky header, resizable columns, sorting, row selection, keyboard nav (↑/↓/Enter/Escape)
- **Right detail drawer** — invoice, customer, laptop, timeline, Tally, audit
- **Status bar** — totals, pagination context, selection

### Table columns
Invoice Number · Invoice Date · Customer · Brand (logo) · Model · Serial (mono) · Store · Payment Mode · Sale Source · Sold By · Amount (—, future) · Status · Actions

### Detail drawer sections
| Section | Content |
|---------|---------|
| Invoice details | Number, date, payment, source, sold by, recorded at |
| Customer | Name, notes |
| Laptop information | Brand, model, serial, store, color, specs |
| Timeline | Sold, marked sold, Tally synced (from audit) |
| Tally information | Company/voucher fields or sync audit entries |
| Audit information | Full audit trail for inventory item |

### Future actions (visible, disabled)
Print invoice · Re-export · Preview PDF — in drawer header and row menu

### Backend
- `GET /api/v1/sales` — wired `sort_field` / `sort_direction` (legacy `sort` param still supported)
- `GET /api/v1/sales/{sale_id}` — full sale detail with laptop specs and Tally fields

### New / updated files
- `components/sales/*` — toolbar, filters, table, drawer, empty state, status bar, timeline, row menu
- `hooks/useSalesWorkspace.ts` — sort, drawer fetch, export, salespeople accumulation
- `lib/sales.ts`, `lib/salesExport.ts`
- `services/api/SalesService.ts` — `getSale()`
- `pages/workspace/SalesPage.tsx` — thin orchestrator

## Verification

```bash
cd apps/desktop && pnpm typecheck && pnpm lint && pnpm test && pnpm build
```

## Screenshots (manual)

| File | Capture |
|------|---------|
| `20-sales-workspace-light.png` | Full sales workspace with data |
| `21-sales-workspace-dark.png` | Dark theme |
| `22-sales-drawer-light.png` | Row selected, drawer open |
| `23-sales-filters-light.png` | Filters visible with active values |

---

**Status: Ready for review.**
