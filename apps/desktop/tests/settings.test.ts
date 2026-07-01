import { describe, expect, it, vi } from 'vitest';
import { canReadSettings, canWriteSettings, canAccessBackupModule, formatBytes, SETTINGS_CATEGORIES, visibleSettingsCategories } from '../src/lib/settings';
import { canManageBackup, canViewBackup } from '../src/services/PermissionService';
import {
  loadAppearancePreferences,
  saveAppearancePreferences,
  type AppearancePreferences,
} from '../src/lib/settingsUi';

describe('settings helpers', () => {
  it('checks settings permissions from backend list', () => {
    expect(canReadSettings(['settings:view', 'auth:login'])).toBe(true);
    expect(canWriteSettings(['settings:modify'])).toBe(true);
    expect(canReadSettings(['auth:login'])).toBe(false);
    expect(canWriteSettings(['settings:view'])).toBe(false);
  });

  it('lists all settings categories', () => {
    const ids = SETTINGS_CATEGORIES.map((item) => item.id);
    expect(ids).toContain('general');
    expect(ids).toContain('backup');
    expect(ids).toContain('about');
    expect(ids).toHaveLength(12);
  });

  it('hides backup category unless backup or restore view is granted', () => {
    const withoutBackup = visibleSettingsCategories(['settings:view']).map((entry) => entry.id);
    expect(withoutBackup).not.toContain('backup');
    const withBackup = visibleSettingsCategories(['backup:view']).map((entry) => entry.id);
    expect(withBackup).toContain('backup');
  });

  it('exposes granular backup permissions', () => {
    expect(canViewBackup(['backup:view'])).toBe(true);
    expect(canManageBackup(['backup:view'])).toBe(false);
    expect(canAccessBackupModule(['restore:view'])).toBe(true);
    expect(canAccessBackupModule(['settings:view'])).toBe(false);
  });

  it('formats byte sizes', () => {
    expect(formatBytes(0)).toBe('0 B');
    expect(formatBytes(1024)).toBe('1.0 KB');
    expect(formatBytes(5 * 1024 * 1024)).toBe('5.0 MB');
  });
});

describe('appearance preferences', () => {
  it('persists compact mode and density to localStorage', () => {
    const storage = new Map<string, string>();
    vi.stubGlobal('localStorage', {
      getItem: (key: string) => storage.get(key) ?? null,
      setItem: (key: string, value: string) => {
        storage.set(key, value);
      },
      removeItem: (key: string) => {
        storage.delete(key);
      },
      clear: () => storage.clear(),
      key: () => null,
      length: 0,
    });
    vi.stubGlobal('document', {
      body: {
        classList: { toggle: vi.fn() },
        dataset: {} as DOMStringMap,
      },
    });

    const prefs: AppearancePreferences = {
      compactMode: true,
      tableDensity: 'compact',
      sidebarBehaviour: 'collapsed',
    };
    saveAppearancePreferences(prefs);
    const loaded = loadAppearancePreferences();
    expect(loaded.compactMode).toBe(true);
    expect(loaded.tableDensity).toBe('compact');
    expect(loaded.sidebarBehaviour).toBe('collapsed');

    saveAppearancePreferences({
      compactMode: false,
      tableDensity: 'comfortable',
      sidebarBehaviour: 'expanded',
    });
    vi.unstubAllGlobals();
  });
});
