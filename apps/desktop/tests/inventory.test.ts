import { describe, expect, it } from 'vitest';
import {
  canMarkSold,
  formatInventorySpecs,
  inventoryStatusBadgeClass,
  inventoryStatusLabel,
} from '../src/lib/inventory';
import {
  hasActiveInventoryFilters,
  inventoryFiltersToExportParams,
} from '../src/lib/inventoryExport';
import {
  colorVariantsLabel,
  modelDisplayName,
  saleStatusBadgeClass,
  saleStatusLabel,
} from '../src/lib/inventoryDomain';
import { DEFAULT_FILTERS } from '../src/hooks/useInventoryWorkspace';

describe('inventory utilities', () => {
  const sampleItem = {
    cpu: 'Intel Core i7',
    ram_gb: 16,
    storage_value: '512',
    storage_unit: 'GB' as const,
    storage_type: 'SSD' as const,
  };

  it('formats specification string', () => {
    expect(formatInventorySpecs(sampleItem)).toBe('Intel Core i7 • 16 GB RAM • 512 GB SSD');
  });

  it('maps status labels and badge classes', () => {
    expect(inventoryStatusLabel('available')).toBe('Available');
    expect(inventoryStatusBadgeClass('reserved', false)).toBe('badge-warning');
    expect(inventoryStatusBadgeClass('available', true)).toBe('badge-neutral');
  });

  it('restricts mark sold to roles with sales:create', () => {
    expect(canMarkSold(['sales:create', 'inventory:view'])).toBe(true);
    expect(canMarkSold(['inventory:view', 'inventory:transfer'])).toBe(false);
  });

  it('maps inventory filters to export params', () => {
    const params = inventoryFiltersToExportParams(
      { ...DEFAULT_FILTERS, brandId: 2, status: 'available' },
      'SN-001',
      'serial_number',
      'asc',
    );
    expect(params.brand_id).toBe(2);
    expect(params.status).toBe('available');
    expect(params.is_archived).toBe(false);
    expect(params.search).toBe('SN-001');
    expect(params.sort_field).toBe('serial_number');
  });

  it('maps created date filters to report date range', () => {
    const params = inventoryFiltersToExportParams(
      { ...DEFAULT_FILTERS, createdDateFrom: '2026-01-01', createdDateTo: '2026-01-31' },
      '',
      'created_at',
      'desc',
    );
    expect(params.date_from).toBe('2026-01-01T00:00:00');
    expect(params.date_to).toBe('2026-01-31T23:59:59');
  });

  it('detects active inventory filters', () => {
    expect(hasActiveInventoryFilters(DEFAULT_FILTERS, '')).toBe(false);
    expect(hasActiveInventoryFilters(DEFAULT_FILTERS, 'test')).toBe(true);
    expect(hasActiveInventoryFilters({ ...DEFAULT_FILTERS, brandId: 1 }, '')).toBe(true);
  });
});

describe('inventory domain helpers', () => {
  it('maps sale status labels and badge classes', () => {
    expect(saleStatusLabel('available', false)).toBe('Not sold');
    expect(saleStatusLabel('sold', false)).toBe('Sold');
    expect(saleStatusLabel('available', true)).toBe('Archived');
    expect(saleStatusBadgeClass('sold', false)).toBe('badge-danger');
    expect(saleStatusBadgeClass('available', false)).toBe('badge-success');
  });

  it('formats model display name and color variants', () => {
    expect(modelDisplayName({ model_number: 'X1515', model_name: 'Vivobook' })).toBe(
      'X1515 — Vivobook',
    );
    expect(colorVariantsLabel(null)).toBe('—');
    expect(colorVariantsLabel({ color_options: 'Quiet Blue, Silver' } as never)).toBe(
      'Quiet Blue, Silver',
    );
  });
});
