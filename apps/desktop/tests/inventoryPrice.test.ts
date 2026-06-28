import { describe, expect, it } from 'vitest';
import { formatInventoryPrice, parsePriceInput } from '../src/lib/inventoryPrice';

describe('inventoryPrice', () => {
  it('parses price input', () => {
    expect(parsePriceInput('54999')).toBe(54999);
    expect(parsePriceInput('54,999')).toBe(54999);
    expect(parsePriceInput('')).toBeNull();
  });

  it('formats inventory price', () => {
    expect(formatInventoryPrice(54999)).toContain('54,999');
  });
});
