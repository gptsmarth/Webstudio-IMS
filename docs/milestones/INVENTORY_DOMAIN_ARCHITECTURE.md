# Inventory Domain Architecture Correction

**Status:** Ready for review  
**Scope:** Desktop UI / frontend architecture (no backend schema changes)

## Domain hierarchy

```
Brand
  └── Product Model (catalogue entry)
        └── Inventory Item (physical unit, serial-tracked)
              └── Sale
```

| Layer | What it is | Owned fields |
|-------|------------|--------------|
| **Product Model** | Catalogue entry (e.g. ASUS Vivobook X1515) | CPU, RAM, Storage, GPU, Image, Color Variants, Generation |
| **Inventory Item** | One physical laptop | Serial Number, Status, Location, Date Added, Unit Color, Sale Status, Audit History, QR Code |
| **Sale** | Transaction linked to a sold unit | Invoice, customer, payment, sold at |

Specifications and images are **never duplicated** on inventory items. The UI inherits them from the parent product model.

## UI changes

### Inventory workspace table

Physical-unit columns only:

- Status, Serial Number, Brand, Product Model, Unit Color, Location, Sale Status, Date Added

Removed from table: CPU, RAM, Storage, Purchase Date, Updated (catalogue or drawer-only fields).

### Inventory detail drawer (section order)

1. **Inventory information** — serial, status, location, date added, unit color, sale status, purchase date
2. **Product model information** — read-only inherited image, brand, model, generation, color variants, specifications
3. **Other units of same model** — sibling serial numbers; click to switch selection
4. **Audit timeline**
5. **Sale information**
6. **Tally information**

Product images in the drawer are **read-only** (`ProductImagePanel` with `readOnly`). Upload is only in Catalogue → Product Models.

### Catalogue → Product Models

- Domain hierarchy hint banner on the tab
- **Color variants** field in create/edit dialog
- **Product image upload** when editing an existing model
- Color variants column in the models table

### New / updated modules

| File | Role |
|------|------|
| `lib/inventoryDomain.ts` | Sale status helpers, model display name, color variant label |
| `components/inventory/InventorySiblingUnits.tsx` | Sibling units list in drawer |
| `hooks/useInventoryWorkspace.ts` | Loads `productModel` + `siblingUnits` for drawer |

## Screenshots (manual)

While `pnpm desktop:dev` is running:

| File | Capture |
|------|---------|
| `40-inventory-table-domain-light.png` | Inventory table — physical-unit columns |
| `41-inventory-drawer-domain-light.png` | Drawer with all six sections visible |
| `42-inventory-siblings-light.png` | Other units of same model section |
| `43-catalogue-model-image-light.png` | Edit product model dialog with image upload |

Save under `docs/milestones/screenshots/`.

## Verification

```bash
cd apps/desktop
pnpm typecheck
pnpm lint
pnpm test
pnpm build
```

## Out of scope (unchanged)

- Warranty and inventory timeline stepper (removed in Milestone 4A)
- Backend API / database schema
- Application redesign or design system changes
