import type { InventoryItemDetail, InventoryStatus, StorageType, StorageUnit } from '../services/api/InventoryService';

export function formatInventorySpecs(item: Pick<InventoryItemDetail, 'cpu' | 'ram_gb' | 'storage_value' | 'storage_unit' | 'storage_type'>): string {
  const storage = formatStorage(item.storage_value, item.storage_unit, item.storage_type);
  return `${item.cpu} • ${item.ram_gb} GB RAM • ${storage}`;
}

/** Comma-separated specs for data tables (no bullet separators). */
export function formatInventorySpecsTable(
  item: Pick<InventoryItemDetail, 'cpu' | 'ram_gb' | 'storage_value' | 'storage_unit' | 'storage_type'>,
): string {
  const storage = formatStorage(item.storage_value, item.storage_unit, item.storage_type);
  return [item.cpu, `${item.ram_gb} GB RAM`, storage].join(', ');
}

export function formatStorage(value: string | number, unit: StorageUnit, type: StorageType): string {
  const numeric = typeof value === 'string' ? value : String(value);
  return `${numeric} ${unit} ${type}`;
}

export function inventoryStatusLabel(status: InventoryStatus): string {
  switch (status) {
    case 'received':
      return 'Received';
    case 'available':
      return 'Available';
    case 'reserved':
      return 'Reserved';
    case 'sold':
      return 'Sold';
    default:
      return status;
  }
}

export function inventoryStatusBadgeClass(status: InventoryStatus, isArchived: boolean): string {
  if (isArchived) return 'badge-neutral';
  switch (status) {
    case 'received':
      return 'badge-primary';
    case 'available':
      return 'badge-success';
    case 'reserved':
      return 'badge-warning';
    case 'sold':
      return 'badge-danger';
    default:
      return 'badge-neutral';
  }
}

export function formatInventoryDate(value: string | null): string {
  if (!value) return '—';
  const timestamp = new Date(value).getTime();
  if (Number.isNaN(timestamp)) return '—';
  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(timestamp);
}

export function canMarkSold(role: string): boolean {
  return role === 'main_admin' || role === 'admin';
}

export function canWriteInventory(role: string): boolean {
  return role === 'main_admin' || role === 'admin';
}

export function canTransferStockLocation(role: string): boolean {
  return role === 'main_admin' || role === 'admin' || role === 'salesperson';
}

export function canViewPurchasePrice(role: string): boolean {
  return role === 'main_admin' || role === 'admin';
}

export function canEditSellingPrice(role: string): boolean {
  return role === 'main_admin' || role === 'admin' || role === 'salesperson';
}
