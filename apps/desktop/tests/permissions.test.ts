import { describe, expect, it } from 'vitest';
import { permissionSet, PermissionService, P } from '../src/services/PermissionService';
import { canEditProductModels, canEditSellingPrice, canEditStockProductModel } from '../src/lib/inventory';

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
    'product_models:edit',
    'product_models:selling_price:edit',
    'inventory:stock_edit',
  ];

  it('allows full stock model edit for salesperson', () => {
    expect(canEditSellingPrice(salesperson)).toBe(true);
    expect(canEditProductModels(salesperson)).toBe(true);
    expect(canEditStockProductModel(salesperson)).toBe(true);
  });

  it('allows stock-only edit without catalogue edit permission', () => {
    const stockEditor = ['inventory:view', 'inventory:stock_edit'];
    expect(canEditStockProductModel(stockEditor)).toBe(true);
    expect(canEditProductModels(stockEditor)).toBe(false);
  });
});
