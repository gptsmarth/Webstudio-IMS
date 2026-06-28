# Milestone 3D — Inventory Workspace (Review)

## Summary

The Inventory page is now the primary operational workspace: searchable, filterable, paginated table with a right-side detail drawer, action dialogs, lifecycle timeline, and product image architecture.

## What was built

### Layout
- Top toolbar: debounced search, filters toggle, refresh, Add Item (disabled — future create flow)
- Collapsible filter panel: brand, location, status, color, warranty preset + date range, purchase dates, include archived, reset + save preset (disabled)
- Sticky-header table with resizable columns, sorting, pagination
- Right detail drawer (400px) with all required sections
- Bottom status bar with selection context

### API integration
- `InventoryService` rewritten against `/api/v1/inventory` (list, get, update, archive, restore, transfer, mark-sold)
- `AuditService` wired to `/api/v1/audit_logs` for drawer timeline and history
- Backend: exposed `color` query param on inventory list (repository already supported it)

### Global search (Cmd/Ctrl+K)
- Live inventory, brand, and location providers
- Clicking a result navigates to Inventory and opens/focuses the item
- Inventory search includes invoice number and customer name (sales table join)

### Product images
- `ProductImageService`: localStorage cache → placeholder → upload prompt
- `REMOTE_FETCH_ENABLED` flag reserved for future internet fetching

### Actions
- Transfer location, Mark sold (admin only), Archive, Restore, Edit (inline drawer fields)
- Print label / Generate QR: visible, disabled (future)

## Verification

Run from repo root:

```bash
cd apps/desktop && pnpm typecheck && pnpm lint && pnpm test && pnpm build
```

## Screenshots

Save captures to [`docs/milestones/screenshots/`](screenshots/) — see [`screenshots/README.md`](screenshots/README.md) for the checklist.

macOS blocked automated window capture (Accessibility permission). With the app running, capture the nine views listed in the README.

| Screen | Light | Dark |
|--------|-------|------|
| Inventory table | `01-table-light.png` | `02-table-dark.png` |
| Detail drawer | `03-drawer-light.png` | `04-drawer-dark.png` |
| Filters panel | `05-filters-light.png` | — |
| Toolbar search | `06-search-light.png` | — |
| Global search | `07-global-search-light.png` | — |
| Transfer dialog | `08-transfer-dialog-light.png` | — |
| Mark sold dialog | `09-mark-sold-dialog-light.png` | — |

## Known limitations (for follow-up)

- Add Item flow not implemented (button placeholder)
- Filter presets UI is future-ready only
- Virtual scrolling not added — server pagination (50/page) used instead
- Salesperson can view inventory but cannot mark sold (by design)

---

**Status: Ready for review.** Do not proceed to other business pages until approved.
