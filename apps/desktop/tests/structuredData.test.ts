import { describe, expect, it } from 'vitest';
import { parseNotificationDescription, structuredRowsFromObject } from '../src/lib/structuredData';

describe('structuredData', () => {
  it('flattens nested location objects into readable rows', () => {
    const rows = structuredRowsFromObject({
      current_location: { id: '2', name: 'Warehouse' },
    });
    expect(rows).toEqual([{ key: 'current_location', label: 'Location', value: 'Warehouse' }]);
  });

  it('humanizes primitive fields', () => {
    const rows = structuredRowsFromObject({
      serial_number: 'SN-100',
      is_active: true,
    });
    expect(rows).toEqual([
      { key: 'serial_number', label: 'Serial number', value: 'SN-100' },
      { key: 'is_active', label: 'Active', value: 'Yes' },
    ]);
  });

  it('parses tally sync notifications into summary and detail rows', () => {
    const parsed = parseNotificationDescription(
      'Tally synchronization started',
      'Synchronization run a156e71e-e69c-48d5-bebb-fec427fb915c started for WEBSTUDIO - (from 1-Apr-2022) - (from 1-Apr-25).',
    );
    expect(parsed.summary).toBe('Tally synchronization started for WEBSTUDIO.');
    expect(parsed.details).toEqual([
      { key: 'sync_run_id', label: 'Sync run ID', value: 'a156e71e-e69c-48d5-bebb-fec427fb915c' },
      { key: 'periods', label: 'Sync periods', value: '1-Apr-2022 · 1-Apr-25' },
    ]);
  });

  it('shortens uuid in generic long descriptions', () => {
    const parsed = parseNotificationDescription(
      'Reference',
      'Operation failed for a156e71e-e69c-48d5-bebb-fec427fb915c during background job.',
    );
    expect(parsed.summary).toContain('a156e71e…');
    expect(parsed.details[0]?.value).toBe('a156e71e-e69c-48d5-bebb-fec427fb915c');
  });
});
