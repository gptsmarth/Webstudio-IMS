import { describe, expect, it } from 'vitest';
import { DEFAULT_SALES_FILTERS } from '../src/hooks/useSalesWorkspace';
import {
  canExportSales,
  formatInvoiceDate,
  saleSourceLabel,
  saleStatusLabel,
} from '../src/lib/sales';
import { hasActiveSalesFilters, salesFiltersToExportParams } from '../src/lib/salesExport';
import { buildSalesTimelineEvents } from '../src/components/sales/SalesTimeline';

describe('sales utilities', () => {
  it('maps sale source and status labels', () => {
    expect(saleSourceLabel('manual')).toBe('Manual');
    expect(saleSourceLabel('tally')).toBe('Tally');
    expect(saleStatusLabel('manual')).toBe('Completed');
    expect(saleStatusLabel('tally')).toBe('Synced');
  });

  it('formats invoice dates', () => {
    expect(formatInvoiceDate('2025-06-15T10:30:00Z')).not.toBe('—');
  });

  it('restricts export to users with sales:export', () => {
    expect(canExportSales(['sales:export', 'sales:view'])).toBe(true);
    expect(canExportSales(['sales:view', 'sales:create'])).toBe(false);
  });

  it('maps sales filters to export params', () => {
    const params = salesFiltersToExportParams(
      { ...DEFAULT_SALES_FILTERS, brandId: 3, saleSource: 'manual' },
      'INV-1',
      'sold_at',
      'desc',
    );
    expect(params.brand_id).toBe(3);
    expect(params.sale_source).toBe('manual');
    expect(params.search).toBe('INV-1');
    expect(params.sort_field).toBe('sold_at');
  });

  it('detects active sales filters', () => {
    expect(hasActiveSalesFilters(DEFAULT_SALES_FILTERS, '')).toBe(false);
    expect(hasActiveSalesFilters(DEFAULT_SALES_FILTERS, 'invoice')).toBe(true);
    expect(hasActiveSalesFilters({ ...DEFAULT_SALES_FILTERS, customerName: 'Acme' }, '')).toBe(true);
  });

  it('builds timeline events from audit logs', () => {
    const events = buildSalesTimelineEvents([
      {
        id: '1',
        entity_type: 'sale',
        entity_id: '1',
        inventory_item_id: 'abc',
        actor_user_id: 1,
        actor_display_name: 'Admin',
        actor_role: 'admin',
        action: 'CREATE',
        source: 'MANUAL',
        field_name: null,
        old_value: null,
        new_value: null,
        description: 'Sale recorded',
        created_at: '2025-06-01T10:00:00Z',
      },
    ], 'Main Store');
    expect(events).toHaveLength(1);
    expect(events[0].label).toBe('Sold');
    expect(events[0].location).toBe('Main Store');
  });
});
