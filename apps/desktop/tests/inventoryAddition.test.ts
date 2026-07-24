import { describe, expect, it } from 'vitest';
import { parseSerialNumbers } from '../src/lib/parseSerialNumbers';
import { summarizeProductModelUnits } from '../src/lib/productModelSummary';
import type { InventoryItemDetail } from '../src/services/api/InventoryService';

describe('parseSerialNumbers', () => {
  it('parses newline-separated serials', () => {
    expect(parseSerialNumbers('SN001\nSN002\nSN003')).toEqual(['SN001', 'SN002', 'SN003']);
  });

  it('parses comma-separated serials and deduplicates case-insensitively', () => {
    expect(parseSerialNumbers('SN001, sn001, SN002')).toEqual(['SN001', 'SN002']);
  });

  it('ignores blank lines', () => {
    expect(parseSerialNumbers('\nSN001\n\n')).toEqual(['SN001']);
  });
});

describe('buildSeededWizardUnits', () => {
  it('prefills every purchase serial when quantity matches', async () => {
    const { buildSeededWizardUnits } = await import('../src/lib/seededWizardUnits');
    const units = buildSeededWizardUnits({
      serials: ['W5PFCJ01V792222', 'W5PFCJ01W077226', 'W5PFCJ01WL1122'],
      unitCount: 3,
      locationId: 79,
      purchasePrice: '49878',
    });
    expect(units).toHaveLength(3);
    expect(units.map((unit) => unit.serial_number)).toEqual([
      'W5PFCJ01V792222',
      'W5PFCJ01W077226',
      'W5PFCJ01WL1122',
    ]);
    expect(units.every((unit) => unit.purchase_price === '49878')).toBe(true);
  });

  it('pads empty rows when quantity exceeds known serials', async () => {
    const { buildSeededWizardUnits } = await import('../src/lib/seededWizardUnits');
    const units = buildSeededWizardUnits({
      serials: ['ONLYONE'],
      unitCount: 3,
      locationId: 1,
      purchasePrice: '100',
    });
    expect(units.map((unit) => unit.serial_number)).toEqual(['ONLYONE', '', '']);
  });
});

describe('summarizeProductModelUnits', () => {
  const base = {
    product_model_id: '1',
    brand_id: 1,
    brand_name: 'ASUS',
    model_number: 'X1515',
    model_name: 'Vivobook',
    cpu: 'i5',
    gpu: null,
    ram_gb: 16,
    storage_value: '512',
    storage_unit: 'GB' as const,
    storage_type: 'SSD' as const,
    color: 'Blue',
    is_archived: false,
    purchase_date: null,
    created_at: '2026-01-10T00:00:00Z',
    updated_at: '2026-01-10T00:00:00Z',
  };

  const items: InventoryItemDetail[] = [
    {
      ...base,
      id: '1',
      serial_number: 'SN001',
      status: 'available',
      current_location_id: 1,
      current_location_name: 'Warehouse',
    },
    {
      ...base,
      id: '2',
      serial_number: 'SN002',
      status: 'sold',
      current_location_id: 1,
      current_location_name: 'Warehouse',
    },
    {
      ...base,
      id: '3',
      serial_number: 'SN003',
      status: 'available',
      current_location_id: 2,
      current_location_name: 'Store',
    },
  ];

  it('aggregates totals and location counts for unsold units', () => {
    const summary = summarizeProductModelUnits(items);
    expect(summary.totalUnits).toBe(3);
    expect(summary.availableUnits).toBe(2);
    expect(summary.soldUnits).toBe(1);
    expect(summary.byLocation).toEqual([
      { locationId: 2, locationName: 'Store', count: 1 },
      { locationId: 1, locationName: 'Warehouse', count: 1 },
    ]);
  });
});
