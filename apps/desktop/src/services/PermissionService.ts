/**
 * Centralized RBAC helpers — single source for permission checks in the desktop UI.
 * Backend `/auth/me` returns the same permission strings; mobile clients can reuse this module.
 */

export const P = {
  inventory: {
    view: 'inventory:view',
    create: 'inventory:create',
    edit: 'inventory:edit',
    stockEdit: 'inventory:stock_edit',
    transfer: 'inventory:transfer',
    archive: 'inventory:archive',
    restore: 'inventory:restore',
    export: 'inventory:export',
  },
  sales: {
    view: 'sales:view',
    create: 'sales:create',
    cancel: 'sales:cancel',
    export: 'sales:export',
  },
  reports: {
    view: 'reports:view',
    export: 'reports:export',
  },
  dashboard: {
    view: 'dashboard:view',
    quickActions: 'dashboard:quick_actions',
    inventoryDistribution: 'dashboard:inventory_distribution',
    brandDistribution: 'dashboard:brand_distribution',
    recentSales: 'dashboard:recent_sales',
    recentInventory: 'dashboard:recent_inventory',
    recentTransfers: 'dashboard:recent_transfers',
    recentActivity: 'dashboard:recent_activity',
    notifications: 'dashboard:notifications',
    storeStatus: 'dashboard:store_status',
    tallyStatus: 'dashboard:tally_status',
    systemStatus: 'dashboard:system_status',
  },
  brands: {
    view: 'brands:view',
    create: 'brands:create',
    edit: 'brands:edit',
    delete: 'brands:delete',
  },
  productModels: {
    view: 'product_models:view',
    create: 'product_models:create',
    edit: 'product_models:edit',
    delete: 'product_models:delete',
    sellingPriceEdit: 'product_models:selling_price:edit',
  },
  locations: {
    view: 'locations:view',
    create: 'locations:create',
    edit: 'locations:edit',
    delete: 'locations:delete',
  },
  users: {
    view: 'users:view',
    create: 'users:create',
    edit: 'users:edit',
    resetPassword: 'users:reset_password',
    activate: 'users:activate',
    deactivate: 'users:deactivate',
  },
  audit: {
    view: 'audit:view',
    export: 'audit:export',
    lifecycle: 'audit:lifecycle',
  },
  notifications: {
    view: 'notifications:view',
    manage: 'notifications:manage',
  },
  settings: {
    view: 'settings:view',
    modify: 'settings:modify',
  },
  backup: {
    view: 'backup:view',
    manage: 'backup:manage',
  },
  restore: {
    view: 'restore:view',
    execute: 'restore:execute',
  },
  tally: {
    viewStatus: 'tally:view_status',
    configure: 'tally:configure',
    runSync: 'tally:run_sync',
    retrySync: 'tally:retry_sync',
  },
} as const;

export type PermissionCode = (typeof P)[keyof typeof P][keyof (typeof P)[keyof typeof P]];

export const DASHBOARD_WIDGET_PERMISSIONS: readonly string[] = [
  P.dashboard.quickActions,
  P.dashboard.inventoryDistribution,
  P.dashboard.brandDistribution,
  P.dashboard.recentSales,
  P.dashboard.recentInventory,
  P.dashboard.recentTransfers,
  P.dashboard.recentActivity,
  P.dashboard.notifications,
  P.dashboard.storeStatus,
  P.dashboard.tallyStatus,
  P.dashboard.systemStatus,
] as const;

const DASHBOARD_WIDGET_SET = new Set<string>(DASHBOARD_WIDGET_PERMISSIONS);

/** Toggle one permission in a custom role editor (mirrors backend normalization rules). */
export function applyCustomRolePermissionToggle(
  selected: ReadonlySet<string>,
  permission: string,
): string[] {
  const next = new Set(selected);
  if (next.has(permission)) {
    next.delete(permission);
    if (permission === P.dashboard.view) {
      for (const widget of DASHBOARD_WIDGET_PERMISSIONS) {
        next.delete(widget);
      }
    }
  } else {
    next.add(permission);
    if (DASHBOARD_WIDGET_SET.has(permission)) {
      next.add(P.dashboard.view);
    }
  }
  return [...next].sort();
}

/** Legacy roles with only dashboard:view still see all widgets until granular picks are saved. */
export function canViewDashboardWidget(permissions: string[], widget: string): boolean {
  const granted = new Set(permissions);
  if (!granted.has(P.dashboard.view)) return false;
  if (granted.has(widget)) return true;
  const hasGranular = DASHBOARD_WIDGET_PERMISSIONS.some((permission) => granted.has(permission));
  return !hasGranular;
}

const ROUTE_PERMISSIONS: Record<string, string> = {
  dashboard: P.dashboard.view,
  stock: P.inventory.view,
  inventory: P.inventory.create,
  sales: P.sales.view,
  catalogue: P.brands.view,
  notifications: P.notifications.view,
  reports: P.reports.view,
  users: P.users.view,
  audit: P.audit.view,
  settings: P.settings.view,
};

export class PermissionService {
  private readonly granted: Set<string>;

  constructor(permissions: string[] | ReadonlySet<string>) {
    this.granted = permissions instanceof Set ? permissions : new Set(permissions);
  }

  static from(permissions: string[] | undefined | null): PermissionService {
    return new PermissionService(permissionSet(permissions));
  }

  has(permission: string): boolean {
    return this.granted.has(permission);
  }

  hasAny(...permissions: string[]): boolean {
    return permissions.some((permission) => this.granted.has(permission));
  }

  hasAll(...permissions: string[]): boolean {
    return permissions.every((permission) => this.granted.has(permission));
  }

  canViewRoute(route: string): boolean {
    const required = ROUTE_PERMISSIONS[route];
    return required ? this.has(required) : false;
  }

  canView(module: keyof typeof P): boolean {
    const group = P[module] as Record<string, string>;
    return this.has(group.view);
  }

  canCreate(module: keyof typeof P): boolean {
    const group = P[module] as Record<string, string>;
    return this.has(group.create);
  }

  canEdit(module: keyof typeof P): boolean {
    const group = P[module] as Record<string, string>;
    return this.has(group.edit);
  }

  canDelete(module: 'brands' | 'productModels' | 'locations'): boolean {
    const legacyMap: Record<string, string> = {
      brands: 'brands:archive',
      productModels: 'product_models:archive',
      locations: 'locations:archive',
    };
    const group = P[module] as Record<string, string>;
    return this.hasAny(group.delete, legacyMap[module]);
  }

  canArchive(module: keyof typeof P): boolean {
    if (module === 'brands' || module === 'productModels' || module === 'locations') {
      return this.canDelete(module);
    }
    const group = P[module] as Record<string, string>;
    return this.has(group.archive);
  }

  canExport(module: 'inventory' | 'sales' | 'reports' | 'audit'): boolean {
    return this.has(P[module].export);
  }

  list(): string[] {
    return [...this.granted].sort();
  }
}

const permissionSetCache = new Map<string, ReadonlySet<string>>();

/** Cached Set lookup for repeated permission checks in a session. */
export function permissionSet(
  permissions: string[] | ReadonlySet<string> | undefined | null,
): ReadonlySet<string> {
  if (permissions instanceof Set) return permissions;
  const list = Array.isArray(permissions) ? permissions : [];
  const key = list.slice().sort().join('\0');
  const cached = permissionSetCache.get(key);
  if (cached) return cached;
  const created = new Set(list);
  permissionSetCache.set(key, created);
  return created;
}

export function permissionDeniedTooltip(permission: string): string {
  return `Requires ${permission} permission`;
}

// Inventory helpers (used across Stock + Inventory workspaces)
export function canMarkSold(permissions: string[]): boolean {
  return PermissionService.from(permissions).has(P.sales.create);
}

export function canWriteInventory(permissions: string[]): boolean {
  const ps = PermissionService.from(permissions);
  return ps.hasAny(P.inventory.create, P.inventory.edit, P.inventory.archive, P.inventory.restore);
}

export function canTransferStockLocation(permissions: string[]): boolean {
  return PermissionService.from(permissions).has(P.inventory.transfer);
}

export function canViewPurchasePrice(permissions: string[]): boolean {
  const ps = PermissionService.from(permissions);
  return ps.hasAny(P.inventory.edit, P.inventory.create, P.productModels.edit);
}

export function canEditSellingPrice(permissions: string[]): boolean {
  return PermissionService.from(permissions).has(P.productModels.sellingPriceEdit);
}

export function canEditStockLaptop(permissions: string[]): boolean {
  return PermissionService.from(permissions).has(P.inventory.stockEdit);
}

export function canEditStockProductModel(permissions: string[]): boolean {
  const ps = PermissionService.from(permissions);
  return ps.hasAny(P.productModels.edit, P.productModels.sellingPriceEdit, P.inventory.stockEdit);
}

export function canEditProductModels(permissions: string[]): boolean {
  return PermissionService.from(permissions).has(P.productModels.edit);
}

export function canWriteCatalogue(permissions: string[]): boolean {
  const ps = PermissionService.from(permissions);
  return ps.hasAny(
    P.brands.create,
    P.brands.edit,
    P.brands.delete,
    'brands:archive',
    P.locations.create,
    P.locations.edit,
    P.locations.delete,
    'locations:archive',
    P.productModels.create,
    P.productModels.edit,
    P.productModels.delete,
    'product_models:archive',
  );
}

export function canExportCatalogue(permissions: string[]): boolean {
  return PermissionService.from(permissions).has(P.reports.export);
}

export function canExportSales(permissions: string[]): boolean {
  return PermissionService.from(permissions).has(P.sales.export);
}

export function canReadSettings(permissions: string[]): boolean {
  return PermissionService.from(permissions).has(P.settings.view);
}

export function canWriteSettings(permissions: string[]): boolean {
  return PermissionService.from(permissions).has(P.settings.modify);
}

export function canViewBackup(permissions: string[]): boolean {
  return PermissionService.from(permissions).has(P.backup.view);
}

export function canManageBackup(permissions: string[]): boolean {
  return PermissionService.from(permissions).has(P.backup.manage);
}

export function canViewRestore(permissions: string[]): boolean {
  return PermissionService.from(permissions).has(P.restore.view);
}

export function canExecuteRestore(permissions: string[]): boolean {
  return PermissionService.from(permissions).has(P.restore.execute);
}

export function canAccessBackupModule(permissions: string[]): boolean {
  return PermissionService.from(permissions).hasAny(P.backup.view, P.restore.view);
}

export function canReadAudit(permissions: string[]): boolean {
  return PermissionService.from(permissions).has(P.audit.view);
}

export function canExportAudit(permissions: string[]): boolean {
  return PermissionService.from(permissions).has(P.audit.export);
}

export function canManageUsers(permissions: string[]): boolean {
  return PermissionService.from(permissions).has(P.users.view);
}

export function canCreateUsers(permissions: string[]): boolean {
  return PermissionService.from(permissions).has(P.users.create);
}

export function canEditUsers(permissions: string[]): boolean {
  return PermissionService.from(permissions).has(P.users.edit);
}

export function canResetUserPassword(permissions: string[]): boolean {
  return PermissionService.from(permissions).has(P.users.resetPassword);
}

export function canActivateUsers(permissions: string[]): boolean {
  return PermissionService.from(permissions).has(P.users.activate);
}

export function canDeactivateUsers(permissions: string[]): boolean {
  return PermissionService.from(permissions).has(P.users.deactivate);
}

export function canExportReports(permissions: string[]): boolean {
  return PermissionService.from(permissions).has(P.reports.export);
}

export function canReadNotifications(permissions: string[]): boolean {
  return PermissionService.from(permissions).has(P.notifications.view);
}

export function canManageNotifications(permissions: string[]): boolean {
  return PermissionService.from(permissions).has(P.notifications.manage);
}

export { ROUTE_PERMISSIONS };
