import { BrandLogoRegistry } from '../registries/BrandLogoRegistry';
import type { StorageType, StorageUnit } from '../services/api/InventoryService';

export type CatalogueTab = 'brands' | 'locations';

import {
  canExportCatalogue as canExportCataloguePermission,
  canWriteCatalogue as canWriteCataloguePermission,
} from '../services/PermissionService';

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

export function confirmCatalogueRemoval(
  label: string,
  kind: 'brand' | 'location' | 'model',
): boolean {
  if (kind === 'brand') {
    return window.confirm(
      `Delete ${label}?\n\nThis permanently removes the brand. Deletion is blocked while product models or inventory still reference it.\n\nPast sales, reports, audit history, and backups are preserved.`,
    );
  }
  if (kind === 'model') {
    return window.confirm(
      `Delete ${label}?\n\nThis permanently removes the product model. Deletion is blocked while inventory items still reference it.\n\nPast sales, reports, audit history, and backups are preserved.`,
    );
  }
  return window.confirm(
    `Delete ${label}?\n\nThis permanently removes the location. Inventory at this location must be transferred first.\n\nPast sales, reports, audit history, and backups are preserved.\n\nThis action cannot be undone.`,
  );
}
