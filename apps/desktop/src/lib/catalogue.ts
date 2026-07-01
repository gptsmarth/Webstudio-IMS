import { BrandLogoRegistry } from '../registries/BrandLogoRegistry';
import type { StorageType, StorageUnit } from '../services/api/InventoryService';

export type CatalogueTab = 'brands' | 'locations';

import { canExportCatalogue as canExportCataloguePermission, canWriteCatalogue as canWriteCataloguePermission } from '../services/PermissionService';

export function canWriteCatalogue(permissions: string[]): boolean {
  return canWriteCataloguePermission(permissions);
}

export function canExportCatalogue(permissions: string[]): boolean {
  return canExportCataloguePermission(permissions);
}

export function brandLogoSrc(name: string, logoFilename?: string | null): string {
  if (logoFilename?.trim()) {
    const file = logoFilename.trim();
    if (file.startsWith('/')) return file;
    return `/assets/brand-logos/${file}`;
  }
  return BrandLogoRegistry.getLogo(name);
}

export function catalogueStatusLabel(active: boolean): string {
  return active ? 'Active' : 'Archived';
}

export function catalogueStatusBadgeClass(active: boolean): string {
  return active ? 'badge-success' : 'badge-neutral';
}

export function locationTypeLabel(type: string): string {
  switch (type) {
    case 'retail_floor':
      return 'Retail floor';
    case 'warehouse':
      return 'Warehouse';
    case 'other':
      return 'Other';
    default:
      return type;
  }
}

export function formatStorageSpec(value: string | number, unit: string, type: string): string {
  return `${value} ${unit} ${type}`;
}

export const STORAGE_UNITS: StorageUnit[] = ['GB', 'TB'];
export const STORAGE_TYPES: StorageType[] = ['SSD', 'HDD'];

export function paginateItems<T>(items: T[], page: number, pageSize: number): T[] {
  const start = (page - 1) * pageSize;
  return items.slice(start, start + pageSize);
}

export function matchesSearch(search: string, values: Array<string | null | undefined>): boolean {
  const term = search.trim().toLowerCase();
  if (!term) return true;
  return values.some((value) => value?.toLowerCase().includes(term));
}

export function catalogueActionErrorMessage(err: unknown): string {
  const api = err as { message?: string };
  return api.message ?? 'Unable to complete this action. Try again.';
}

export function confirmCatalogueRemoval(label: string, kind: 'brand' | 'location' | 'model'): boolean {
  const noun = kind === 'brand' ? 'brand' : kind === 'location' ? 'location' : 'product model';
  if (kind === 'model' || kind === 'brand') {
    return window.confirm(
      `Delete ${label}?\n\nThis permanently removes the ${noun}${kind === 'brand' ? ' and all of its product models' : ''} and all serial numbers still in stock. Past sales records and audit history are kept with the details recorded at the time of sale.`,
    );
  }
  return window.confirm(
    `Remove ${label}?\n\nThis hides the ${noun} from Stock and new entries. Sales and inventory history are preserved. Turn on "Show archived" to restore it later.`,
  );
}
