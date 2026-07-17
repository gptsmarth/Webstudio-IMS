/// Display grouping for custom access role editor (mirrors desktop userPermissions).
class PermissionGroup {
  const PermissionGroup({required this.label, required this.permissions});

  final String label;
  final List<PermissionOption> permissions;
}

class PermissionOption {
  const PermissionOption({
    required this.id,
    required this.label,
    required this.description,
  });

  final String id;
  final String label;
  final String description;
}

const List<PermissionGroup> kAssignablePermissionGroups = [
  PermissionGroup(
    label: 'Dashboard',
    permissions: [
      PermissionOption(
        id: 'dashboard:view',
        label: 'View dashboard',
        description: 'Open the Dashboard tab',
      ),
      PermissionOption(
        id: 'dashboard:quick_actions',
        label: 'Quick actions',
        description: 'Shortcut actions on the dashboard',
      ),
      PermissionOption(
        id: 'dashboard:inventory_distribution',
        label: 'Inventory distribution',
        description: 'Available stock and location breakdown',
      ),
      PermissionOption(
        id: 'dashboard:brand_distribution',
        label: 'Brand distribution',
        description: 'Stock by brand summary',
      ),
      PermissionOption(
        id: 'dashboard:recent_sales',
        label: 'Recent sales',
        description: 'Latest sold units',
      ),
      PermissionOption(
        id: 'dashboard:recent_inventory',
        label: 'Recent inventory additions',
        description: 'New serial numbers registered',
      ),
      PermissionOption(
        id: 'dashboard:recent_transfers',
        label: 'Recent transfers',
        description: 'Location movement feed',
      ),
      PermissionOption(
        id: 'dashboard:recent_activity',
        label: 'Recent activity',
        description: 'Audit and system activity timeline',
      ),
      PermissionOption(
        id: 'dashboard:notifications',
        label: 'Notifications panel',
        description: 'Unresolved alerts on the dashboard',
      ),
      PermissionOption(
        id: 'dashboard:store_status',
        label: 'Store status',
        description: 'Operational stock by location',
      ),
      PermissionOption(
        id: 'dashboard:tally_status',
        label: 'Tally status',
        description: 'Synchronization readiness widget',
      ),
      PermissionOption(
        id: 'dashboard:system_status',
        label: 'System status',
        description: 'API and database health',
      ),
    ],
  ),
  PermissionGroup(
    label: 'Stock',
    permissions: [
      PermissionOption(
        id: 'inventory:view',
        label: 'View stock tab',
        description: 'Browse brands, models, and serials',
      ),
      PermissionOption(
        id: 'inventory:transfer',
        label: 'Transfer stock',
        description: 'Move units between locations',
      ),
      PermissionOption(
        id: 'inventory:stock_edit',
        label: 'Edit laptop in stock',
        description: 'Update model specs and selling price from Stock',
      ),
    ],
  ),
  PermissionGroup(
    label: 'Inventory (admin)',
    permissions: [
      PermissionOption(id: 'inventory:create', label: 'Add laptops', description: 'Inventory tab — receive stock'),
      PermissionOption(id: 'inventory:edit', label: 'Edit items', description: 'Update serial details'),
      PermissionOption(id: 'inventory:archive', label: 'Archive', description: 'Archive inventory units'),
      PermissionOption(id: 'inventory:restore', label: 'Restore', description: 'Restore archived units'),
      PermissionOption(id: 'inventory:export', label: 'Export', description: 'Export inventory data'),
    ],
  ),
  PermissionGroup(
    label: 'Sales',
    permissions: [
      PermissionOption(id: 'sales:view', label: 'View sales', description: 'Open Sales tab'),
      PermissionOption(id: 'sales:create', label: 'Record sales', description: 'Create sale records'),
      PermissionOption(id: 'sales:cancel', label: 'Cancel sales', description: 'Cancel transactions'),
      PermissionOption(id: 'sales:export', label: 'Export sales', description: 'Export sales data'),
    ],
  ),
  PermissionGroup(
    label: 'Purchase',
    permissions: [
      PermissionOption(
        id: 'purchase:view',
        label: 'View purchase queue',
        description: 'Review Tally purchase vouchers awaiting import',
      ),
      PermissionOption(
        id: 'purchase:import',
        label: 'Import to inventory',
        description: 'Import verified purchase stock into inventory',
      ),
    ],
  ),
  PermissionGroup(
    label: 'Reports',
    permissions: [
      PermissionOption(id: 'reports:view', label: 'View reports', description: 'Open Report Center'),
      PermissionOption(id: 'reports:export', label: 'Export reports', description: 'Download reports'),
    ],
  ),
  PermissionGroup(
    label: 'Catalogue',
    permissions: [
      PermissionOption(id: 'brands:view', label: 'View brands', description: 'Catalogue tab'),
      PermissionOption(id: 'brands:create', label: 'Create brands', description: 'Add brands'),
      PermissionOption(id: 'brands:edit', label: 'Edit brands', description: 'Update brands'),
      PermissionOption(id: 'product_models:view', label: 'View models', description: 'Browse models'),
      PermissionOption(id: 'product_models:edit', label: 'Edit models', description: 'Update model specs'),
      PermissionOption(id: 'product_models:selling_price:edit', label: 'Edit selling price', description: 'From stock cards'),
      PermissionOption(id: 'locations:view', label: 'View locations', description: 'Browse locations'),
    ],
  ),
  PermissionGroup(
    label: 'Backup & recovery',
    permissions: [
      PermissionOption(
        id: 'backup:view',
        label: 'View backups',
        description: 'Backup status, history, and downloads',
      ),
      PermissionOption(
        id: 'backup:manage',
        label: 'Manage backups',
        description: 'Run backups and configure retention',
      ),
      PermissionOption(
        id: 'restore:view',
        label: 'View recovery',
        description: 'Recovery center and restore preview',
      ),
      PermissionOption(
        id: 'restore:execute',
        label: 'Execute restore',
        description: 'Import archives and restore the database',
      ),
    ],
  ),
  PermissionGroup(
    label: 'Settings & Tally',
    permissions: [
      PermissionOption(id: 'settings:view', label: 'View settings', description: 'Open Settings tab'),
      PermissionOption(id: 'tally:view_status', label: 'Tally status', description: 'View sync status'),
      PermissionOption(id: 'tally:run_sync', label: 'Run Tally sync', description: 'Trigger synchronisation'),
    ],
  ),
  PermissionGroup(
    label: 'Audit & Notifications',
    permissions: [
      PermissionOption(id: 'audit:view', label: 'Audit logs', description: 'Audit center'),
      PermissionOption(id: 'audit:lifecycle', label: 'Serial history', description: 'Lifecycle timeline'),
      PermissionOption(id: 'notifications:view', label: 'Notifications', description: 'Read alerts'),
      PermissionOption(id: 'notifications:manage', label: 'Manage notifications', description: 'Resolve alerts'),
    ],
  ),
];

List<String> get allAssignablePermissionIds => kAssignablePermissionGroups
    .expand((group) => group.permissions.map((option) => option.id))
    .toList();
