# Milestone 4A — Inventory Workspace (Review)

## Summary

The Inventory Workspace is now a full desktop operations surface: always-visible filters, toolbar primary actions, split specification columns, row action menu, keyboard navigation, add/transfer/sold/export dialogs, and polished empty states — aligned with the approved design system.

**Intentional exclusions** (per prior approval in this milestone cycle):

- **Warranty** — removed from filters, table, drawer, and backend (migration `0015`)
- **Timeline stepper** — removed from detail drawer (audit history remains)

## What was built

### Page layout
- **Top toolbar:** debounced global search, Add Laptop, Transfer, Mark Sold, Export (XLSX), Refresh
- **Filters panel:** always visible — brand, location, status, color, purchase date range, include archived, reset
- **Inventory table:** sticky header, resizable columns, sortable fields, row hover/selection, keyboard navigation (↑/↓/Enter/Escape)
- **Right detail drawer:** product image, overview, specs, purchase, location, audit history, sale, Tally
- **Bottom pagination** in table footer + status bar

### Table columns
Status · Serial (mono) · Brand (logo) · Model · CPU · RAM · Storage · Color · Location · Purchase Date · Updated · Actions

### Primary actions
| Action | Entry points |
|--------|----------------|
| Add Laptop | Toolbar, empty state |
| Transfer | Toolbar, drawer, row menu |
| Mark Sold | Toolbar, drawer, row menu (admin) |
| Export | Toolbar → inventory XLSX via ReportService |
| Refresh | Toolbar |

### Dialogs
- **Add Inventory** — serial, brand → model cascade, color, location, status, purchase date
- **Transfer Location** — existing dialog, wired from toolbar + row menu
- **Mark Sold** — existing dialog, wired from toolbar + row menu

### Row actions menu
View · Edit · Transfer · Mark Sold · Archive · Restore · Generate QR (future) · Print Label (future)

### Empty & loading states
- `InventoryEmptyState` with filter-aware copy and actions
- Skeleton rows only while loading (no blank table)

### New / updated files
- `AddInventoryDialog.tsx`
- `InventoryRowActionsMenu.tsx`
- `InventoryEmptyState.tsx`
- `lib/inventoryExport.ts`
- `useInventoryWorkspace.ts` — `createItem`, `exportInventory`, `loadProductModels`
- `InventoryTable.tsx`, `InventoryToolbar.tsx`, `InventoryPage.tsx` — full wiring

## Verification

```bash
cd apps/desktop && pnpm typecheck && pnpm lint && pnpm test && pnpm build
```

All checks passed at handoff.

## Screenshots

Save captures to [`docs/milestones/screenshots/`](screenshots/). Suggested 4A additions:

| File | How to capture |
|------|----------------|
| `10-workspace-light.png` | Full workspace — filters visible, table populated |
| `11-workspace-dark.png` | Same view, dark theme |
| `12-add-dialog-light.png` | Add Laptop dialog open |
| `13-row-menu-light.png` | Row actions menu open |
| `14-empty-state-light.png` | Empty or zero-result state |

Existing 3D captures (`01`–`09`) remain valid for drawer, transfer, and mark-sold flows.

## Known limitations

- Export is XLSX only from toolbar (PDF available via Reports builder)
- Filter presets: UI placeholder only
- Generate QR / Print label: disabled (future)
- Product image remote lookup: architecture flag only
- Server pagination (50/page) — no virtual scroll

---

**Status: Ready for review.** Awaiting approval before next milestone.
