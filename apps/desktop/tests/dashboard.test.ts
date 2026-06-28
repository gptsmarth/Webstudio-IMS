import { describe, expect, it } from 'vitest';
import { formatActivityType, locationSharePercent } from '../src/lib/dashboard';

describe('dashboard utilities', () => {
  it('formats activity labels', () => {
    expect(formatActivityType('location_transfer')).toBe('Location transfer');
  });

  it('calculates location share percent', () => {
    expect(locationSharePercent(25, 100)).toBe(25);
    expect(locationSharePercent(0, 0)).toBe(0);
  });
});
