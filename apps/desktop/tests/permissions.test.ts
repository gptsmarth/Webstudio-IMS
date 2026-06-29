import { describe, expect, it } from 'vitest';
import { permissionSet, PermissionService, P } from '../src/services/PermissionService';
import { canEditProductModels, canEditSellingPrice } from '../src/lib/inventory';

describe('permission set cache', () => {
  it('reuses cached sets for identical permission lists', () => {
    const first = permissionSet(['inventory:view', 'sales:view']);
    const second = permissionSet(['sales:view', 'inventory:view']);
    expect(first).toBe(second);
    expect(PermissionService.from(first).has(P.inventory.view)).toBe(true);
  });
});

describe('stock model edit permissions', () => {
  const salesperson = [
    'auth:login',
    'inventory:view',
    'product_models:view',
    'product_models:selling_price:edit',
  ];

  it('allows selling price edit without full model edit', () => {
    expect(canEditSellingPrice(salesperson)).toBe(true);
    expect(canEditProductModels(salesperson)).toBe(false);
  });
});
