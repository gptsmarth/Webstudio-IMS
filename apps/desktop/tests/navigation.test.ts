import { describe, expect, it } from 'vitest';
import {
  defaultRouteForPermissions,
  isRouteAllowedForPermissions,
  isStockOnlyUser,
  navItemsForPermissions,
  NAV_ITEMS,
} from '../src/config/navigation';

const MAIN_ADMIN_PERMS = [
  'users:view',
  'users:create',
  'inventory:view',
  'inventory:create',
  'inventory:edit',
  'inventory:transfer',
  'inventory:archive',
  'inventory:restore',
  'inventory:export',
  'purchase:view',
  'purchase:import',
  'sales:view',
  'sales:create',
  'dashboard:view',
  'brands:view',
  'reports:view',
  'audit:view',
  'notifications:view',
  'settings:view',
];

const STOCK_ONLY_PERMS = ['inventory:view', 'dashboard:view'];

const SALESPERSON_PERMS = [
  'inventory:view',
  'inventory:transfer',
  'sales:view',
  'dashboard:view',
  'brands:view',
  'product_models:view',
  'locations:view',
  'notifications:view',
];

describe('navigation config', () => {
  it('shows all modules for main admin permissions', () => {
    expect(navItemsForPermissions(MAIN_ADMIN_PERMS)).toHaveLength(NAV_ITEMS.length);
  });

  it('shows stock and dashboard for stock-only permissions', () => {
    const ids = navItemsForPermissions(STOCK_ONLY_PERMS).map((item) => item.id);
    expect(ids).toContain('stock');
    expect(ids).toContain('dashboard');
    expect(ids).not.toContain('sales');
    expect(ids).not.toContain('catalogue');
    expect(ids).not.toContain('notifications');
    expect(ids).not.toContain('inventory');
    expect(ids).not.toContain('users');
    expect(ids).not.toContain('settings');
    expect(isStockOnlyUser(STOCK_ONLY_PERMS)).toBe(true);
  });

  it('shows sales and catalogue when salesperson permissions include them', () => {
    const ids = navItemsForPermissions(SALESPERSON_PERMS).map((item) => item.id);
    expect(ids).toContain('sales');
    expect(ids).toContain('catalogue');
    expect(ids).toContain('notifications');
    expect(isStockOnlyUser(SALESPERSON_PERMS)).toBe(true);
  });

  it('defaults salesperson to stock when dashboard unavailable', () => {
    expect(defaultRouteForPermissions(SALESPERSON_PERMS)).toBe('dashboard');
    expect(defaultRouteForPermissions(['inventory:view'])).toBe('stock');
  });

  it('blocks routes without permission', () => {
    expect(isRouteAllowedForPermissions('stock', SALESPERSON_PERMS)).toBe(true);
    expect(isRouteAllowedForPermissions('inventory', SALESPERSON_PERMS)).toBe(false);
    expect(isRouteAllowedForPermissions('users', SALESPERSON_PERMS)).toBe(false);
  });
});
