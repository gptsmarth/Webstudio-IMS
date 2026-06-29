import {
  canReadSettings as canReadSettingsPermission,
  canWriteSettings as canWriteSettingsPermission,
} from '../services/PermissionService';

export type SettingsCategory =
  | 'general'
  | 'security'
  | 'inventory'
  | 'sales'
  | 'tally'
  | 'integrations'
  | 'excel'
  | 'notifications'
  | 'backup'
  | 'appearance'
  | 'system'
  | 'about';

export const SETTINGS_CATEGORIES: { id: SettingsCategory; label: string }[] = [
  { id: 'general', label: 'Company' },
  { id: 'appearance', label: 'Branding' },
  { id: 'security', label: 'Security' },
  { id: 'integrations', label: 'Integrations' },
  { id: 'inventory', label: 'Inventory' },
  { id: 'sales', label: 'Sales' },
  { id: 'tally', label: 'Tally' },
  { id: 'excel', label: 'Excel' },
  { id: 'notifications', label: 'Notifications' },
  { id: 'backup', label: 'Backup' },
  { id: 'system', label: 'System' },
  { id: 'about', label: 'Version' },
];

export function canReadSettings(permissions: string[]): boolean {
  return canReadSettingsPermission(permissions);
}

export function canWriteSettings(permissions: string[]): boolean {
  return canWriteSettingsPermission(permissions);
}

export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** index;
  return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}
