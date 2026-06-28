import { describe, expect, it } from 'vitest';
import { VOUCHER_TYPE_STORE_MAP, MONITORED_VOUCHER_TYPES } from '../src/lib/tally';
import { formatBytes } from '../src/lib/settings';

describe('tally integration helpers', () => {
  it('maps voucher types to stores', () => {
    expect(VOUCHER_TYPE_STORE_MAP.Sales).toBe('WEBSTUDIO');
    expect(VOUCHER_TYPE_STORE_MAP['NEW SALE']).toBe('AES');
  });

  it('monitors both sales voucher types', () => {
    expect(MONITORED_VOUCHER_TYPES).toContain('Sales');
    expect(MONITORED_VOUCHER_TYPES).toContain('NEW SALE');
  });
});

describe('settings helpers still work', () => {
  it('formats bytes', () => {
    expect(formatBytes(2048)).toBe('2.0 KB');
  });
});
