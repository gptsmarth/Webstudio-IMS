# Product Architecture Revision — Review

This revision supersedes the previous KPI-style dashboard. Visual design language is unchanged.

## What changed

### Removed from product surface
- Reserved / Pending Warranty / Sold Today / Sold This Month / Archived KPI cards
- Dashboard `sales_summary` and warranty insight payloads
- Hardcoded store name matching in distribution widget
- Reserved status in inventory filter dropdown (DB status remains for legacy data)

### Dashboard → Operations Center
Layout order:
1. Greeting + Quick Actions
2. **Inventory Distribution** (total available + all active locations, dynamic)
3. **Brand Distribution** (table with logos — no charts)
4. Recent Activity
5. Notifications
6. **Store Status**
7. Tally Status

### Sidebar (new order)
Dashboard → Inventory → **Sales** → Brands → Product Models → Locations → Notifications → **Reports & Export** → Users → Audit Logs → Settings

### New modules
- **Sales Workspace** — independent table, filters, detail drawer (`GET /api/v1/sales`)
- **Reports & Export Center** — sectioned export UI wired to `/api/v1/reports/export`

### Universal search
Added Sales provider (invoice/customer/serial). Inventory, brand, location retained.

## API changes

| Endpoint | Change |
|----------|--------|
| `GET /api/v1/dashboard` | Returns `{ total_available_inventory, as_of }` only |
| `GET /api/v1/dashboard/distribution` | Adds `total_available_inventory` |
| `GET /api/v1/sales` | **New** — paginated sales list (`sales:read`) |

## Verification

```bash
cd apps/desktop && pnpm typecheck && pnpm lint && pnpm test && pnpm build
cd apps/backend && pytest tests/dashboard tests/reports -q
```

## Screenshots

Capture light/dark for: sidebar, operations dashboard, inventory, sales, reports center. See `docs/milestones/screenshots/README.md`.

## Development order (remaining)

3. Brands  
4. Product Models  
5. Locations  
6. Reports refinements (preview panes, custom filters)  
7. Notifications  
8. Audit Logs  
9. Settings  
10. Universal Search (users, audit, tally logs)  
11. Tally integration  
12. Desktop packaging  
13. Android  

**Stop here for review** before continuing down the list.
