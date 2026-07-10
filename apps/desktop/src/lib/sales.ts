import {
  canExportSales as canExportSalesPermission,
  P,
  PermissionService,
} from '../services/PermissionService';
import { formatInventoryDate, formatStorage } from './inventory';
import type { SaleDetail } from '../services/api/SalesService';
import type { StorageType, StorageUnit } from '../services/api/InventoryService';

export function saleSourceLabel(source: string): string {
  switch (source) {
    case 'manual':
      return 'Manual';
    case 'tally':
      return 'Tally';
    default:
      return source;
  }
}

/** Operator-facing Tally invoice processing status (from backend label). */
export function tallyInvoiceStatusLabel(status: string | null | undefined): string {
  switch (status) {
    case 'processed':
      return 'Processed';
    case 'processed_with_warnings':
      return 'Processed With Warnings';
    case 'skipped':
      return 'Skipped';
    case 'failed':
      return 'Failed';
    default:
      return status ? status.replaceAll('_', ' ') : '—';
  }
}

export function saleSourceBadgeClass(source: string): string {
  switch (source) {
    case 'manual':
      return 'badge-success';
    case 'tally':
      return 'badge-primary';
    default:
      return 'badge-neutral';
  }
}

export function saleStatusLabel(source: string): string {
  return source === 'tally' ? 'Synced' : 'Completed';
}

export function saleStatusBadgeClass(source: string): string {
  return source === 'tally' ? 'badge-primary' : 'badge-success';
}

export function formatSaleSpecs(
  item: Pick<SaleDetail, 'cpu' | 'ram_gb' | 'storage_value' | 'storage_unit' | 'storage_type'>,
): string {
  const storage = formatStorage(
    item.storage_value,
    item.storage_unit as StorageUnit,
    item.storage_type as StorageType,
  );
  return `${item.cpu} • ${item.ram_gb} GB RAM • ${storage}`;
}

export function canExportSales(permissions: string[]): boolean {
  return canExportSalesPermission(permissions);
}

export function canCancelSales(permissions: string[]): boolean {
  return PermissionService.from(permissions).has(P.sales.cancel);
}

export function formatInvoiceDate(value: string): string {
  return formatInventoryDate(value);
}

export function formatSaleAmount(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—';
  const amount = typeof value === 'string' ? Number(value) : value;
  if (Number.isNaN(amount)) return '—';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatSaleAmountBreakdown(
  inclusive: number | null | undefined,
  excludingGst: number | null | undefined,
): { listLabel: string; detailInclusive: string; detailExcluding: string | null } {
  const listLabel = formatSaleAmount(inclusive);
  const detailInclusive = formatSaleAmount(inclusive);
  const detailExcluding =
    excludingGst === null || excludingGst === undefined ? null : formatSaleAmount(excludingGst);
  return { listLabel, detailInclusive, detailExcluding };
}
