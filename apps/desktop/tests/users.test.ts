import { describe, expect, it } from 'vitest';
import { assessPasswordStrength, generateTemporaryPassword } from '../src/lib/passwordStrength';
import { buildPermissionModules } from '../src/lib/userPermissions';
import {
  canDisableUser,
  canManageUsers,
  userDisplayName,
  userInitials,
} from '../src/lib/users';
import type { UserDetail } from '../src/services/api/UserService';

function user(overrides: Partial<UserDetail> = {}): UserDetail {
  return {
    id: 2,
    username: 'sales1',
    display_name: 'Sales One',
    role: 'salesperson',
    status: 'active',
    must_change_password: false,
    theme_preference: null,
    last_login_at: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    permissions: [],
    ...overrides,
  };
}

describe('users helpers', () => {
  it('checks users:manage permission from backend list', () => {
    expect(canManageUsers(['users:manage', 'auth:login'])).toBe(true);
    expect(canManageUsers(['auth:login'])).toBe(false);
  });

  it('formats display name and initials', () => {
    expect(userDisplayName({ username: 'admin', display_name: 'Main Admin' })).toBe('Main Admin');
    expect(userInitials({ username: 'admin', display_name: 'Main Admin' })).toBe('MA');
  });

  it('blocks disabling the logged-in main admin', () => {
    const mainAdmin = user({ id: 1, role: 'main_admin' });
    const result = canDisableUser(mainAdmin, 1, 2);
    expect(result.allowed).toBe(false);
    expect(result.reason).toMatch(/own Main Administrator/i);
  });

  it('blocks disabling the last active main admin', () => {
    const mainAdmin = user({ id: 3, role: 'main_admin' });
    const result = canDisableUser(mainAdmin, 1, 1);
    expect(result.allowed).toBe(false);
    expect(result.reason).toMatch(/last active Main Administrator/i);
  });
});

describe('password strength', () => {
  it('requires minimum length', () => {
    const weak = assessPasswordStrength('short');
    expect(weak.meetsMinimum).toBe(false);
    const strong = assessPasswordStrength('LongEnough1!');
    expect(strong.meetsMinimum).toBe(true);
  });

  it('generates passwords meeting minimum length', () => {
    const generated = generateTemporaryPassword();
    expect(generated.length).toBeGreaterThanOrEqual(14);
    expect(assessPasswordStrength(generated).meetsMinimum).toBe(true);
  });
});

describe('permission viewer grouping', () => {
  it('marks granted permissions from backend payload', () => {
    const modules = buildPermissionModules(['inventory:read', 'sales:read']);
    const inventory = modules.find((group) => group.module === 'Inventory');
    const sales = modules.find((group) => group.module === 'Sales');
    expect(inventory?.capabilities.find((cap) => cap.label === 'Read')?.granted).toBe(true);
    expect(inventory?.capabilities.find((cap) => cap.label === 'Create / Update')?.granted).toBe(false);
    expect(sales?.capabilities.find((cap) => cap.label === 'View')?.granted).toBe(true);
  });
});
