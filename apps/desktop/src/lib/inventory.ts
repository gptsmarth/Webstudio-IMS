import type {
  InventoryItemDetail,
  InventoryStatus,
  StorageType,
  StorageUnit,
} from '../services/api/InventoryService';
import type { ProductModel } from '../services/api/ProductModelService';
import { accessoryKindLabel, isAccessoryModel } from './productCategory';
import {
  canEditProductModels as canEditProductModelsPermission,
  canEditSellingPrice as canEditSellingPricePermission,
  canEditStockLaptop as canEditStockLaptopPermission,
  canEditStockProductModel as canEditStockProductModelPermission,
  canMarkSold as canMarkSoldPermission,
  canTransferStockLocation as canTransferStockLocationPermission,
  canViewPurchasePrice as canViewPurchasePricePermission,
  canWriteInventory as canWriteInventoryPermission,
  P,
  PermissionService,
} from '../services/PermissionService';

export function formatInventorySpecs(
  item: Pick<
    InventoryItemDetail | ProductModel,
    | 'cpu'
    | 'ram_gb'
    | 'storage_value'
    | 'storage_unit'
    | 'storage_type'
    | 'category'
    | 'accessory_kind'
    | 'part_number'
    | 'model_number'
  >,
): string {
  if (isAccessoryModel(item)) {
    const parts = [accessoryKindLabel(item.accessory_kind)];
    if (item.part_number && item.part_number !== item.model_number) {
      parts.push(`PN ${item.part_number}`);
    }
    return parts.join(' • ');
  }
  if (!item.cpu || item.ram_gb == null) {
    return '—';
  }
  const storage = formatStorage(
    item.storage_value ?? '',
    item.storage_unit ?? 'GB',
    item.storage_type ?? 'SSD',
  );
  return `${item.cpu} • ${item.ram_gb} GB RAM • ${storage}`;
}

/** Comma-separated specs for data tables (no bullet separators). */
export function formatInventorySpecsTable(
  item: Pick<
    InventoryItemDetail | ProductModel,
    | 'cpu'
    | 'ram_gb'
    | 'storage_value'
    | 'storage_unit'
    | 'storage_type'
    | 'category'
    | 'accessory_kind'
    | 'part_number'
    | 'model_number'
  >,
): string {
  if (isAccessoryModel(item)) {
    const parts = [accessoryKindLabel(item.accessory_kind)];
    if (item.part_number && item.part_number !== item.model_number) {
      parts.push(`PN ${item.part_number}`);
    }
    return parts.join(', ');
  }
  if (!item.cpu || item.ram_gb == null) {
    return '—';
  }
  const storage = formatStorage(
    item.storage_value ?? '',
    item.storage_unit ?? 'GB',
    item.storage_type ?? 'SSD',
  );
  return [item.cpu, `${item.ram_gb} GB RAM`, storage].join(', ');
}

export function formatStorage(
  value: string | number,
  unit: StorageUnit,
  type: StorageType,
): string {
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
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(timestamp);
}

export function canMarkSold(permissions: string[]): boolean {
  return canMarkSoldPermission(permissions);
}

export function canWriteInventory(permissions: string[]): boolean {
  return canWriteInventoryPermission(permissions);
}

export function canTransferStockLocation(permissions: string[]): boolean {
  return canTransferStockLocationPermission(permissions);
}

export function canDeleteInventorySerial(permissions: string[]): boolean {
  return PermissionService.from(permissions).has(P.inventory.archive);
}

export function canViewPurchasePrice(permissions: string[]): boolean {
  return canViewPurchasePricePermission(permissions);
}

export function canEditSellingPrice(permissions: string[]): boolean {
  return canEditSellingPricePermission(permissions);
}

export function canEditStockLaptop(permissions: string[]): boolean {
  return canEditStockLaptopPermission(permissions);
}

export function canEditStockProductModel(permissions: string[]): boolean {
  return canEditStockProductModelPermission(permissions);
}

export function canEditProductModels(permissions: string[]): boolean {
  return canEditProductModelsPermission(permissions);
}

export function canArchiveProductModels(permissions: string[]): boolean {
  return PermissionService.from(permissions).hasAny(
    P.productModels.delete,
    'product_models:archive',
  );
}
