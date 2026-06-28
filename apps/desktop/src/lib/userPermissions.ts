/** Display grouping for backend permission strings (presentation only). */

export interface PermissionCapability {
  label: string;
  permission: string;
}

export interface PermissionModuleGroup {
  module: string;
  capabilities: { label: string; granted: boolean }[];
}

const MODULE_DEFINITIONS: { module: string; capabilities: PermissionCapability[] }[] = [
  {
    module: 'Users',
    capabilities: [{ label: 'Manage', permission: 'users:manage' }],
  },
  {
    module: 'Inventory',
    capabilities: [
      { label: 'Read', permission: 'inventory:read' },
      { label: 'Create / Update', permission: 'inventory:write' },
      { label: 'Status transitions', permission: 'inventory:transition' },
      { label: 'Transfer location', permission: 'location:transfer' },
    ],
  },
  {
    module: 'Catalogue',
    capabilities: [
      { label: 'Read brands', permission: 'brands:read' },
      { label: 'Write brands', permission: 'brands:write' },
      { label: 'Read models', permission: 'product_models:read' },
      { label: 'Write models', permission: 'product_models:write' },
      { label: 'Archive models', permission: 'product_models:archive' },
    ],
  },
  {
    module: 'Sales',
    capabilities: [
      { label: 'View', permission: 'sales:read' },
      { label: 'Mark sold', permission: 'sales:reflect' },
    ],
  },
  {
    module: 'Reports',
    capabilities: [{ label: 'Export', permission: 'reports:read' }],
  },
  {
    module: 'Audit',
    capabilities: [
      { label: 'Lifecycle events', permission: 'audit:lifecycle' },
      { label: 'Read logs', permission: 'audit:read' },
    ],
  },
  {
    module: 'Dashboard',
    capabilities: [{ label: 'View', permission: 'dashboard:read' }],
  },
  {
    module: 'Notifications',
    capabilities: [
      { label: 'Read', permission: 'notifications:read' },
      { label: 'Resolve', permission: 'notifications:resolve' },
    ],
  },
  {
    module: 'Locations',
    capabilities: [
      { label: 'Read', permission: 'locations:read' },
      { label: 'Write', permission: 'locations:write' },
    ],
  },
  {
    module: 'Settings',
    capabilities: [
      { label: 'Read', permission: 'settings:read' },
      { label: 'Write', permission: 'settings:write' },
    ],
  },
  {
    module: 'Tally',
    capabilities: [
      { label: 'Sync', permission: 'tally:sync' },
      { label: 'Dashboard', permission: 'tally:dashboard' },
      { label: 'Notifications', permission: 'tally:notifications' },
      { label: 'Admin', permission: 'tally:admin' },
    ],
  },
  {
    module: 'Sync',
    capabilities: [{ label: 'Trigger', permission: 'sync:trigger' }],
  },
];

export function buildPermissionModules(permissions: string[]): PermissionModuleGroup[] {
  const granted = new Set(permissions);
  return MODULE_DEFINITIONS.map((definition) => ({
    module: definition.module,
    capabilities: definition.capabilities.map((cap) => ({
      label: cap.label,
      granted: granted.has(cap.permission),
    })),
  })).filter((group) => group.capabilities.some((cap) => cap.granted) || group.module === 'Settings');
}

export function listUnknownPermissions(permissions: string[]): string[] {
  const known = new Set(
    MODULE_DEFINITIONS.flatMap((group) => group.capabilities.map((cap) => cap.permission)),
  );
  return permissions.filter((permission) => !known.has(permission)).sort();
}
