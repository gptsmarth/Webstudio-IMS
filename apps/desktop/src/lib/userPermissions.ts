/** Display grouping and metadata for backend permission strings (presentation only). */

import { resolveEffectivePermissions, type PermissionGrantSource } from './permissionArchitecture';
import { filterPermissionsByLicense, createLicensePermissionContext } from './permissionLicense';

export type PermissionModuleId =
  | 'dashboard'
  | 'stock'
  | 'inventory'
  | 'sales'
  | 'reports'
  | 'catalogue'
  | 'administration'
  | 'settings'
  | 'tally'
  | 'audit'
  | 'notifications'
  | 'other';

export interface PermissionMetadata {
  permission: string;
  label: string;
  description: string;
  module: PermissionModuleId;
  /** Stable key for future localization (permission.{module}.{action}). */
  i18nKey: string;
}

export interface PermissionCapabilityView {
  label: string;
  permission: string;
  description: string;
  granted: boolean;
  inheritedFrom: string;
  source: PermissionGrantSource;
}

export interface PermissionModuleGroup {
  module: string;
  moduleId: PermissionModuleId;
  capabilities: PermissionCapabilityView[];
  grantedCount: number;
}

export const PERMISSION_MODULE_ORDER: { id: PermissionModuleId; label: string }[] = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'stock', label: 'Stock' },
  { id: 'inventory', label: 'Inventory (admin)' },
  { id: 'sales', label: 'Sales' },
  { id: 'reports', label: 'Reports' },
  { id: 'catalogue', label: 'Catalogue' },
  { id: 'administration', label: 'Administration' },
  { id: 'settings', label: 'Settings' },
  { id: 'tally', label: 'Tally' },
  { id: 'audit', label: 'Audit' },
  { id: 'notifications', label: 'Notifications' },
  { id: 'other', label: 'Other' },
];

const PERMISSION_REGISTRY: PermissionMetadata[] = [
  { permission: 'dashboard:view', label: 'View dashboard', description: 'Open the Dashboard tab', module: 'dashboard', i18nKey: 'permission.dashboard.view' },
  { permission: 'dashboard:quick_actions', label: 'Quick actions', description: 'Shortcut bar (add laptop, search, transfer, etc.)', module: 'dashboard', i18nKey: 'permission.dashboard.quick_actions' },
  { permission: 'dashboard:inventory_distribution', label: 'Inventory distribution', description: 'Available stock by location chart', module: 'dashboard', i18nKey: 'permission.dashboard.inventory_distribution' },
  { permission: 'dashboard:brand_distribution', label: 'Brand distribution', description: 'Stock breakdown by brand', module: 'dashboard', i18nKey: 'permission.dashboard.brand_distribution' },
  { permission: 'dashboard:recent_sales', label: 'Recent sales', description: 'Latest sold units feed', module: 'dashboard', i18nKey: 'permission.dashboard.recent_sales' },
  { permission: 'dashboard:recent_inventory', label: 'Recent inventory additions', description: 'Newly registered serial numbers', module: 'dashboard', i18nKey: 'permission.dashboard.recent_inventory' },
  { permission: 'dashboard:recent_transfers', label: 'Recent transfers', description: 'Location movement feed', module: 'dashboard', i18nKey: 'permission.dashboard.recent_transfers' },
  { permission: 'dashboard:recent_activity', label: 'Recent activity', description: 'Combined activity timeline', module: 'dashboard', i18nKey: 'permission.dashboard.recent_activity' },
  { permission: 'dashboard:notifications', label: 'Notifications panel', description: 'Unresolved alerts on the dashboard', module: 'dashboard', i18nKey: 'permission.dashboard.notifications' },
  { permission: 'dashboard:store_status', label: 'Store status', description: 'Operational stock by location', module: 'dashboard', i18nKey: 'permission.dashboard.store_status' },
  { permission: 'dashboard:tally_status', label: 'Tally status', description: 'Synchronization readiness widget', module: 'dashboard', i18nKey: 'permission.dashboard.tally_status' },
  { permission: 'dashboard:system_status', label: 'System status', description: 'API and database health', module: 'dashboard', i18nKey: 'permission.dashboard.system_status' },
  { permission: 'inventory:view', label: 'View stock tab', description: 'Browse brands, models, and serial numbers in Stock', module: 'stock', i18nKey: 'permission.stock.view' },
  { permission: 'inventory:stock_edit', label: 'Edit laptop in stock', description: 'Update model specs and selling price from Stock', module: 'stock', i18nKey: 'permission.inventory.stock_edit' },
  { permission: 'inventory:create', label: 'Create', description: 'Add inventory items (Inventory tab)', module: 'inventory', i18nKey: 'permission.inventory.create' },
  { permission: 'inventory:edit', label: 'Edit', description: 'Update inventory item details', module: 'inventory', i18nKey: 'permission.inventory.edit' },
  { permission: 'inventory:transfer', label: 'Transfer', description: 'Move stock between locations', module: 'stock', i18nKey: 'permission.inventory.transfer' },
  { permission: 'inventory:archive', label: 'Archive', description: 'Archive inventory items', module: 'inventory', i18nKey: 'permission.inventory.archive' },
  { permission: 'inventory:restore', label: 'Restore', description: 'Restore archived inventory', module: 'inventory', i18nKey: 'permission.inventory.restore' },
  { permission: 'inventory:export', label: 'Export', description: 'Export inventory data', module: 'inventory', i18nKey: 'permission.inventory.export' },
  { permission: 'sales:view', label: 'View', description: 'View sales records', module: 'sales', i18nKey: 'permission.sales.view' },
  { permission: 'sales:create', label: 'Create', description: 'Record new sales', module: 'sales', i18nKey: 'permission.sales.create' },
  { permission: 'sales:cancel', label: 'Cancel', description: 'Cancel sales transactions', module: 'sales', i18nKey: 'permission.sales.cancel' },
  { permission: 'sales:export', label: 'Export', description: 'Export sales data', module: 'sales', i18nKey: 'permission.sales.export' },
  { permission: 'reports:view', label: 'View', description: 'Open reports workspace', module: 'reports', i18nKey: 'permission.reports.view' },
  { permission: 'reports:export', label: 'Export', description: 'Export report outputs', module: 'reports', i18nKey: 'permission.reports.export' },
  { permission: 'brands:view', label: 'View brands', description: 'Browse product brands', module: 'catalogue', i18nKey: 'permission.brands.view' },
  { permission: 'brands:create', label: 'Create brands', description: 'Add new brands', module: 'catalogue', i18nKey: 'permission.brands.create' },
  { permission: 'brands:edit', label: 'Edit brands', description: 'Update brand details', module: 'catalogue', i18nKey: 'permission.brands.edit' },
  { permission: 'brands:archive', label: 'Delete brands', description: 'Permanently delete brands', module: 'catalogue', i18nKey: 'permission.brands.archive' },
  { permission: 'product_models:view', label: 'View models', description: 'Browse product models', module: 'catalogue', i18nKey: 'permission.product_models.view' },
  { permission: 'product_models:create', label: 'Create models', description: 'Add product models', module: 'catalogue', i18nKey: 'permission.product_models.create' },
  { permission: 'product_models:edit', label: 'Edit models', description: 'Update full model specifications', module: 'catalogue', i18nKey: 'permission.product_models.edit' },
  { permission: 'product_models:archive', label: 'Archive models', description: 'Archive product models', module: 'catalogue', i18nKey: 'permission.product_models.archive' },
  { permission: 'product_models:selling_price:edit', label: 'Edit selling price', description: 'Update selling price from stock', module: 'catalogue', i18nKey: 'permission.product_models.selling_price.edit' },
  { permission: 'locations:view', label: 'View locations', description: 'Browse store locations', module: 'catalogue', i18nKey: 'permission.locations.view' },
  { permission: 'locations:create', label: 'Create locations', description: 'Add store locations', module: 'catalogue', i18nKey: 'permission.locations.create' },
  { permission: 'locations:edit', label: 'Edit locations', description: 'Update location details', module: 'catalogue', i18nKey: 'permission.locations.edit' },
  { permission: 'locations:archive', label: 'Archive locations', description: 'Archive locations', module: 'catalogue', i18nKey: 'permission.locations.archive' },
  { permission: 'users:view', label: 'View', description: 'Open user administration', module: 'administration', i18nKey: 'permission.users.view' },
  { permission: 'users:create', label: 'Create', description: 'Create user accounts', module: 'administration', i18nKey: 'permission.users.create' },
  { permission: 'users:edit', label: 'Edit', description: 'Update user profiles', module: 'administration', i18nKey: 'permission.users.edit' },
  { permission: 'users:reset_password', label: 'Reset password', description: 'Reset user passwords', module: 'administration', i18nKey: 'permission.users.reset_password' },
  { permission: 'users:activate', label: 'Activate', description: 'Activate user accounts', module: 'administration', i18nKey: 'permission.users.activate' },
  { permission: 'users:deactivate', label: 'Deactivate', description: 'Deactivate user accounts', module: 'administration', i18nKey: 'permission.users.deactivate' },
  { permission: 'settings:view', label: 'View', description: 'Open system settings', module: 'settings', i18nKey: 'permission.settings.view' },
  { permission: 'settings:modify', label: 'Modify', description: 'Change system settings', module: 'settings', i18nKey: 'permission.settings.modify' },
  { permission: 'backup:view', label: 'View backups', description: 'View backup status, history, and downloads', module: 'settings', i18nKey: 'permission.backup.view' },
  { permission: 'backup:manage', label: 'Manage backups', description: 'Run backups and configure retention policy', module: 'settings', i18nKey: 'permission.backup.manage' },
  { permission: 'restore:view', label: 'View recovery', description: 'Open recovery center and preview restores', module: 'settings', i18nKey: 'permission.restore.view' },
  { permission: 'restore:execute', label: 'Execute restore', description: 'Import archives and restore or roll back the database', module: 'settings', i18nKey: 'permission.restore.execute' },
  { permission: 'tally:view_status', label: 'View status', description: 'View Tally sync status', module: 'tally', i18nKey: 'permission.tally.view_status' },
  { permission: 'tally:configure', label: 'Configure', description: 'Configure Tally integration', module: 'tally', i18nKey: 'permission.tally.configure' },
  { permission: 'tally:run_sync', label: 'Run sync', description: 'Start Tally synchronisation', module: 'tally', i18nKey: 'permission.tally.run_sync' },
  { permission: 'tally:retry_sync', label: 'Retry sync', description: 'Retry failed Tally sync jobs', module: 'tally', i18nKey: 'permission.tally.retry_sync' },
  { permission: 'audit:view', label: 'View logs', description: 'Browse audit logs', module: 'audit', i18nKey: 'permission.audit.view' },
  { permission: 'audit:export', label: 'Export', description: 'Export audit logs', module: 'audit', i18nKey: 'permission.audit.export' },
  { permission: 'audit:lifecycle', label: 'Serial lifecycle', description: 'View serial lifecycle history', module: 'audit', i18nKey: 'permission.audit.lifecycle' },
  { permission: 'notifications:view', label: 'View', description: 'Read notifications', module: 'notifications', i18nKey: 'permission.notifications.view' },
  { permission: 'notifications:manage', label: 'Manage', description: 'Resolve and manage notifications', module: 'notifications', i18nKey: 'permission.notifications.manage' },
  { permission: 'auth:login', label: 'Sign in', description: 'Authenticate to the application', module: 'other', i18nKey: 'permission.auth.login' },
  { permission: 'sync:worker', label: 'Sync worker', description: 'Background sync service account', module: 'other', i18nKey: 'permission.sync.worker' },
  { permission: 'tally:worker', label: 'Tally worker', description: 'Tally integration worker', module: 'other', i18nKey: 'permission.tally.worker' },
  { permission: 'health:integrations', label: 'Integration health', description: 'Read integration health probes', module: 'other', i18nKey: 'permission.health.integrations' },
];

const REGISTRY_BY_PERMISSION = new Map(PERMISSION_REGISTRY.map((entry) => [entry.permission, entry]));

export function getPermissionMetadata(permission: string): PermissionMetadata | undefined {
  return REGISTRY_BY_PERMISSION.get(permission);
}

export function buildPermissionModules(
  permissions: string[],
  options?: { roleLabel?: string },
): PermissionModuleGroup[] {
  const roleLabel = options?.roleLabel ?? 'Role';
  const licenseContext = createLicensePermissionContext();
  const licensed = filterPermissionsByLicense(permissions, licenseContext);
  const granted = new Set(licensed);
  const effective = resolveEffectivePermissions({
    rolePermissions: licensed,
    roleLabel,
  });
  const effectiveByPermission = new Map(effective.map((entry) => [entry.permission, entry]));

  const groups = PERMISSION_MODULE_ORDER.map(({ id, label }) => {
    const capabilities = PERMISSION_REGISTRY
      .filter((entry) => entry.module === id)
      .map((entry) => {
        const grant = effectiveByPermission.get(entry.permission);
        const isGranted = granted.has(entry.permission);
        return {
          label: entry.label,
          permission: entry.permission,
          description: entry.description,
          granted: isGranted,
          inheritedFrom: grant?.inheritedFrom ?? roleLabel,
          source: grant?.source ?? 'role',
        };
      });
    const grantedCount = capabilities.filter((cap) => cap.granted).length;
    return {
      module: label,
      moduleId: id,
      capabilities,
      grantedCount,
    };
  });

  const known = new Set(PERMISSION_REGISTRY.map((entry) => entry.permission));
  const unknown = licensed.filter((permission) => !known.has(permission)).sort();
  if (unknown.length > 0) {
    const otherGroup = groups.find((group) => group.moduleId === 'other');
    const extra = unknown.map((permission) => ({
      label: permission,
      permission,
      description: 'Additional capability',
      granted: true,
      inheritedFrom: roleLabel,
      source: 'role' as const,
    }));
    if (otherGroup) {
      otherGroup.capabilities.push(...extra);
      otherGroup.grantedCount += extra.length;
    }
  }

  return groups;
}

export function filterPermissionModules(
  modules: PermissionModuleGroup[],
  query: string,
): PermissionModuleGroup[] {
  const term = query.trim().toLowerCase();
  if (!term) return modules;

  return modules
    .map((group) => ({
      ...group,
      capabilities: group.capabilities.filter((cap) => (
        cap.label.toLowerCase().includes(term)
        || cap.permission.toLowerCase().includes(term)
        || cap.description.toLowerCase().includes(term)
        || group.module.toLowerCase().includes(term)
      )),
      grantedCount: 0,
    }))
    .map((group) => ({
      ...group,
      grantedCount: group.capabilities.filter((cap) => cap.granted).length,
    }))
    .filter((group) => group.capabilities.length > 0);
}

export function listUnknownPermissions(permissions: string[]): string[] {
  const known = new Set(PERMISSION_REGISTRY.map((entry) => entry.permission));
  return permissions.filter((permission) => !known.has(permission)).sort();
}

/** Count capabilities granted from the role permission list (matches backend payload size). */
export function countGrantedPermissions(permissions: string[]): number {
  return permissions.length;
}

export function totalDefinedPermissions(): number {
  return PERMISSION_REGISTRY.length;
}
