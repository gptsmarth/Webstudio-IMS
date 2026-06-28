/** Store mapping and voucher types for Tally ERP 9 integration. */

export const MONITORED_VOUCHER_TYPES = ['Sales', 'NEW SALE'] as const;

export const VOUCHER_TYPE_STORE_MAP: Record<string, string> = {
  Sales: 'WEBSTUDIO',
  'NEW SALE': 'AES',
};

export type MonitoredVoucherType = (typeof MONITORED_VOUCHER_TYPES)[number];

export function storeForVoucherType(voucherType: string): string | null {
  return VOUCHER_TYPE_STORE_MAP[voucherType] ?? null;
}

export function isMonitoredVoucherType(voucherType: string): boolean {
  return MONITORED_VOUCHER_TYPES.includes(voucherType as MonitoredVoucherType);
}
