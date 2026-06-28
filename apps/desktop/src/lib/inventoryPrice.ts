import { formatSaleAmount } from './sales';

export function formatInventoryPrice(value: number | string | null | undefined): string {
  return formatSaleAmount(value);
}

export function parsePriceInput(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const normalized = trimmed.replace(/,/g, '');
  const amount = Number(normalized);
  if (Number.isNaN(amount) || amount < 0) return null;
  return amount;
}
