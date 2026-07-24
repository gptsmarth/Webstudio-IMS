import { describe, expect, it } from 'vitest';
import { assessPasswordStrength, generateTemporaryPassword } from '../src/lib/passwordStrength';
import { buildPermissionModules, countGrantedPermissions } from '../src/lib/userPermissions';
import {
  canArchiveUser,
  canDisableUser,
  canManageUsers,
  canRestoreUser,
  formatPasswordAge,
  userDisplayName,
  userEffectiveStatus,
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
    failed_login_count: 0,
    is_locked: false,
    is_archived: false,
    active_session_count: 0,
    password_age_days: null,
    created_by_display_name: null,
    locked_until: null,
    password_changed_at: null,
    created_by_user_id: null,
    archived_at: null,
    sessions: [],
    login_events: [],
    ...overrides,
  };
}

describe('users helpers', () => {
  it('checks users:view permission from backend list', () => {
    expect(canManageUsers(['users:view', 'auth:login'])).toBe(true);
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

  it('derives effective status labels', () => {
    expect(userEffectiveStatus({ status: 'active', is_archived: true }).label).toBe('Archived');
    expect(userEffectiveStatus({ status: 'active', is_locked: true }).label).toBe('Locked');
    expect(formatPasswordAge(3)).toBe('3 days');
  });

  it('controls archive and restore eligibility', () => {
    const archived = user({ is_archived: true });
    expect(canRestoreUser(archived)).toBe(true);
    expect(canArchiveUser(archived, 1, 2).allowed).toBe(false);
  });
});

describe('password strength', () => {
  it('requires length, upper, lower, and number like the server policy', () => {
    expect(assessPasswordStrength('short').meetsMinimum).toBe(false);
    expect(assessPasswordStrength('longenough1').meetsMinimum).toBe(false); // no uppercase
    expect(assessPasswordStrength('LONGENOUGH1').meetsMinimum).toBe(false); // no lowercase
    expect(assessPasswordStrength('LongEnough').meetsMinimum).toBe(false); // no number
    expect(assessPasswordStrength('LongEnough1!').meetsMinimum).toBe(true);
  });

  it('generates passwords meeting minimum length', () => {
    const generated = generateTemporaryPassword();
    expect(generated.length).toBeGreaterThanOrEqual(14);
    expect(assessPasswordStrength(generated).meetsMinimum).toBe(true);
  });
});

describe('permission viewer grouping', () => {
  it('marks granted permissions from backend payload', () => {
    const modules = buildPermissionModules(['inventory:view', 'sales:view'], {
      roleLabel: 'Salesperson',
    });
    const stock = modules.find((group) => group.moduleId === 'stock');
    const inventory = modules.find((group) => group.moduleId === 'inventory');
    const sales = modules.find((group) => group.moduleId === 'sales');
    expect(stock?.capabilities.find((cap) => cap.label === 'View stock tab')?.granted).toBe(true);
    expect(inventory?.capabilities.find((cap) => cap.label === 'Create')?.granted).toBe(false);
    expect(sales?.capabilities.find((cap) => cap.label === 'View')?.granted).toBe(true);
    expect(stock?.capabilities[0]?.inheritedFrom).toBe('Salesperson');
  });

  it('counts granted permissions from role payload', () => {
    expect(countGrantedPermissions(['inventory:view', 'sales:view'])).toBe(2);
  });
});
