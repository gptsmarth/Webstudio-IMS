import { describe, expect, it } from 'vitest';
import {
  defaultRouteForRole,
  isRouteAllowedForRole,
  navItemsForRole,
  NAV_ITEMS,
} from '../src/config/navigation';

describe('navigation config', () => {
  it('shows all modules for main_admin', () => {
    expect(navItemsForRole('main_admin')).toHaveLength(NAV_ITEMS.length);
  });

  it('restricts salesperson to stock only', () => {
    const ids = navItemsForRole('salesperson').map((item) => item.id);
    expect(ids).toEqual(['stock']);
    expect(ids).not.toContain('dashboard');
    expect(ids).not.toContain('inventory');
    expect(ids).not.toContain('sales');
    expect(ids).not.toContain('catalogue');
    expect(ids).not.toContain('notifications');
    expect(ids).not.toContain('users');
    expect(ids).not.toContain('reports');
    expect(ids).not.toContain('settings');
  });

  it('defaults salesperson to stock and blocks admin routes', () => {
    expect(defaultRouteForRole('salesperson')).toBe('stock');
    expect(defaultRouteForRole('admin')).toBe('dashboard');
    expect(isRouteAllowedForRole('stock', 'salesperson')).toBe(true);
    expect(isRouteAllowedForRole('dashboard', 'salesperson')).toBe(false);
    expect(isRouteAllowedForRole('sales', 'salesperson')).toBe(false);
  });

  it('shows inventory for admin', () => {
    const ids = navItemsForRole('admin').map((item) => item.id);
    expect(ids).toContain('inventory');
    expect(ids).toContain('stock');
    expect(ids).toContain('reports');
    expect(ids).not.toContain('users');
    expect(ids).not.toContain('settings');
  });
});
