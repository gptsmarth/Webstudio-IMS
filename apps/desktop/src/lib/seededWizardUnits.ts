export interface SeededWizardUnit {
  serial_number: string;
  current_location_id: number;
  purchase_price: string;
}

/**
 * Build wizard unit rows from purchase-import seeds.
 * Count is max(serials, requested unit count), capped at 50.
 */
export function buildSeededWizardUnits(options: {
  serials?: string[] | null;
  unitCount?: number | null;
  locationId: number;
  purchasePrice?: string | null;
}): SeededWizardUnit[] {
  const seeded = (options.serials ?? []).map((serial) => serial.trim()).filter(Boolean);
  const requested = Math.max(0, Math.floor(options.unitCount ?? 0));
  const count = Math.max(1, Math.min(50, Math.max(seeded.length, requested, 1)));
  const purchasePrice = options.purchasePrice ?? '';
  return Array.from({ length: count }, (_, index) => ({
    serial_number: seeded[index] ?? '',
    current_location_id: options.locationId,
    purchase_price: purchasePrice,
  }));
}
