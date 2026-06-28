# Milestone 4C — Catalogue Management (Review)

## Summary

Catalogue Management is a unified tabbed workspace for **Brands**, **Product Models**, and **Locations**, aligned with the Inventory and Sales workspace patterns.

## What was built

### Navigation
- Single **Catalogue** nav item replaces separate Brands / Product Models / Locations entries
- Route: `catalogue`

### Tabs
| Tab | Table columns |
|-----|----------------|
| Brands | Logo, Name, Models, Available, Sold, Status, Actions |
| Product Models | Brand, Model, CPU, GPU, RAM, Storage, Generation, Available, Sold, Image, Status, Actions |
| Locations | Location, Type, Current Stock, Capacity, Status, Actions |

### Shared features (every tab)
- Search (debounced client-side)
- Sortable columns
- Pagination (25 per page)
- Filters (brand / type / include archived)
- Add / Edit dialogs
- Archive / Restore (row menu)
- Export (CSV, admin only)
- Skeleton loaders + empty states
- Role gating: salesperson read-only; admin/main_admin can write

### Stock aggregates
- Available / sold counts from `GET /api/v1/dashboard/distribution`
- Models count per brand computed client-side
- Location capacity uses total units at location (future dedicated capacity field)

### Services extended
- `BrandService` — full CRUD + archive/restore
- `ProductModelService` — full types + CRUD + archive/restore
- `LocationService` — full CRUD + archive/restore

### New files
- `pages/workspace/CataloguePage.tsx`
- `components/catalogue/*` — tabs, toolbar, tables, dialogs
- `hooks/useCatalogueDistribution.ts`
- `lib/catalogue.ts`, `lib/catalogueExport.ts`

## Verification

```bash
cd apps/desktop && pnpm typecheck && pnpm lint && pnpm test && pnpm build
```

## Screenshots (manual)

| File | Capture |
|------|---------|
| `30-catalogue-brands-light.png` | Brands tab |
| `31-catalogue-models-light.png` | Product Models tab |
| `32-catalogue-locations-light.png` | Locations tab |
| `33-catalogue-dialog-light.png` | Add/Edit dialog |

---

**Status: Ready for review.**
