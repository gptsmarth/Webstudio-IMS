# Inventory Addition Workflow

**Status:** Ready for review  
**Scope:** Desktop UI + inventory list date filter (backend)

## Business rule

A **product model is created once** in the catalogue. Every shipment adds **inventory items** (serial numbers) linked to the existing model — never a duplicate catalogue entry.

```
ASUS Vivobook X1515 (product model)
  ├── SN001 … SN005   (shipment 1)
  └── SN006 … SN010   (shipment 2 — same model)
```

## Add inventory dialog

Workflow:

1. Choose **brand**
2. **Use existing product model** or **create new product model**
3. Enter **one or many serial numbers** (newline or comma separated)
4. Choose **location** and **unit color**
5. Save — creates N inventory items under the selected model

When an existing model is selected, **Product Model Summary** shows:

- Total units · Available · Sold
- Units grouped by location (all locations supported)

## Created date (not purchase date)

- **Purchase date** removed from add dialog, detail drawer, and inventory filters
- **Date added** (`created_at`) is the inventory item timestamp (set by the server on create)
- Inventory filters and exports use **date added** range
- Inventory reports filter by **date added** (`date_from` / `date_to` on `created_at`)

## New modules

| File | Role |
|------|------|
| `lib/parseSerialNumbers.ts` | Bulk serial parsing + deduplication |
| `lib/productModelSummary.ts` | Fetch + aggregate units per model |
| `components/inventory/ProductModelSummaryPanel.tsx` | Summary UI in add dialog and drawer |
| `components/inventory/AddInventoryDialog.tsx` | Full workflow with model mode toggle |

## Screenshots (manual)

| File | Capture |
|------|---------|
| `50-add-inventory-existing-model-light.png` | Add dialog — existing model + summary |
| `51-add-inventory-bulk-serials-light.png` | Bulk serial textarea with count hint |
| `52-add-inventory-new-model-light.png` | Create new product model inline |
| `53-drawer-model-summary-light.png` | Drawer product model summary |

## Verification

```bash
pnpm typecheck
pnpm lint
cd apps/desktop && pnpm test && pnpm build
```
