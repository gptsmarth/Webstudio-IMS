import { describe, expect, it } from 'vitest';
import {
  buildReportQueryParams,
  DEFAULT_REPORT_FILTERS,
  tallyOutcomeNotificationType,
} from '../src/lib/reportBuilder';
import { dateInputToRange, resolveDatePreset } from '../src/lib/reportDatePresets';

describe('reportDatePresets', () => {
  it('resolves today preset with bounded range', () => {
    const range = resolveDatePreset('today');
    expect(range.from).toBeTruthy();
    expect(range.to).toBeTruthy();
    expect(new Date(range.to).getTime()).toBeGreaterThanOrEqual(new Date(range.from).getTime());
  });

  it('maps custom date inputs to ISO range', () => {
    const range = dateInputToRange('2026-01-01', '2026-01-31');
    expect(range.from).toContain('2026-01-01');
    expect(range.to).toContain('2026-01-31');
  });
});

describe('reportBuilder', () => {
  it('maps inventory status filters', () => {
    const available = buildReportQueryParams(
      'inventory',
      {
        ...DEFAULT_REPORT_FILTERS,
        inventoryStatus: 'available',
      },
      1,
      50,
      'created_at',
      'desc',
    );
    expect(available.status).toBe('available');
    expect(available.is_archived).toBe(false);

    const archived = buildReportQueryParams(
      'inventory',
      {
        ...DEFAULT_REPORT_FILTERS,
        inventoryStatus: 'archived',
      },
      1,
      50,
      null,
      'desc',
    );
    expect(archived.is_archived).toBe(true);
  });

  it('maps inventory created date preset to query range', () => {
    const params = buildReportQueryParams(
      'inventory',
      {
        ...DEFAULT_REPORT_FILTERS,
        datePreset: 'month',
      },
      1,
      50,
      null,
      'desc',
    );
    expect(params.date_from).toBeTruthy();
    expect(params.date_to).toBeTruthy();
  });

  it('maps tally outcome filters to notification types', () => {
    expect(tallyOutcomeNotificationType('duplicate')).toBe('duplicate_sale');
    expect(tallyOutcomeNotificationType('missing_serial')).toBe('serial_number_missing');
    const params = buildReportQueryParams(
      'tally',
      {
        ...DEFAULT_REPORT_FILTERS,
        tallyOutcome: 'processed',
      },
      1,
      50,
      null,
      'desc',
    );
    expect(params.notification_category).toBe('tally_sync');
    expect(params.notification_type).toBe('tally_sync_completed');
  });

  it('requires preview workflow — export params mirror active filters', () => {
    const params = buildReportQueryParams(
      'sales',
      {
        ...DEFAULT_REPORT_FILTERS,
        invoiceNumber: 'INV-100',
        saleSource: 'manual',
      },
      2,
      50,
      'sold_at',
      'asc',
    );
    expect(params.invoice_number).toBe('INV-100');
    expect(params.sale_source).toBe('manual');
    expect(params.page).toBe(2);
    expect(params.sort_field).toBe('sold_at');
    expect(params.sort_direction).toBe('asc');
  });
});
