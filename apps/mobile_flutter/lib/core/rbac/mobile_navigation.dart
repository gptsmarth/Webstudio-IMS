import 'package:flutter/material.dart';

import 'role_permissions.dart';
import '../../features/auth/domain/auth_models.dart';

/// Mirrors desktop `PermissionService` / `navigation.ts` for mobile shell routing.
class MobileNavItem {
  const MobileNavItem({
    required this.branchIndex,
    required this.label,
    required this.icon,
    required this.selectedIcon,
  });

  final int branchIndex;
  final String label;
  final IconData icon;
  final IconData selectedIcon;
}

/// Branch indices — must match [app_router.dart] StatefulShellRoute order.
abstract final class MobileShellBranch {
  static const dashboard = 0;
  static const stock = 1;
  static const inventory = 2;
  static const sales = 3;
  static const catalogue = 4;
  static const more = 5;
  static const settings = 6;
}

bool isStockOnlyUser(List<String> permissions) {
  return permissions.contains('inventory:view') && !permissions.contains('inventory:create');
}

bool canViewSalesModule(List<String> permissions) {
  return permissions.contains('sales:view');
}

bool canViewCatalogueModule(List<String> permissions) {
  return permissions.contains('brands:view');
}

bool canViewAdminSettings(List<String> permissions) => permissions.contains('settings:view');

bool canViewBackup(List<String> permissions) => permissions.contains('backup:view');

bool canManageBackup(List<String> permissions) => permissions.contains('backup:manage');

bool canViewRestore(List<String> permissions) => permissions.contains('restore:view');

bool canExecuteRestore(List<String> permissions) => permissions.contains('restore:execute');

bool canAccessBackupModule(List<String> permissions) =>
    canViewBackup(permissions) || canViewRestore(permissions);

bool canEditSellingPrice(List<String> permissions) =>
    permissions.contains('product_models:selling_price:edit');

bool canEditStockLaptop(List<String> permissions) =>
    permissions.contains('inventory:stock_edit');

bool canEditProductModels(List<String> permissions) =>
    permissions.contains('product_models:edit');

/// Stock model detail — edit specs, price, notes, and image from the Stock tab.
bool canEditStockProductModel(List<String> permissions) =>
    canEditProductModels(permissions) ||
    canEditSellingPrice(permissions) ||
    canEditStockLaptop(permissions);

bool _hasMoreAccess(List<String> permissions) {
  return permissions.contains('reports:view') ||
      permissions.contains('notifications:view') ||
      permissions.contains('users:view') ||
      permissions.contains('settings:view') ||
      permissions.contains('tally:view_status') ||
      permissions.contains('audit:view');
}

List<MobileNavItem> mobileNavItemsFor(List<String> permissions) {
  final items = <MobileNavItem>[];

  if (permissions.contains('dashboard:view')) {
    items.add(const MobileNavItem(
      branchIndex: MobileShellBranch.dashboard,
      label: 'Dashboard',
      icon: Icons.dashboard_outlined,
      selectedIcon: Icons.dashboard,
    ));
  }

  if (permissions.contains('inventory:view')) {
    items.add(const MobileNavItem(
      branchIndex: MobileShellBranch.stock,
      label: 'Stock',
      icon: Icons.inventory_2_outlined,
      selectedIcon: Icons.inventory_2,
    ));
  }

  if (permissions.contains('inventory:create')) {
    items.add(const MobileNavItem(
      branchIndex: MobileShellBranch.inventory,
      label: 'Inventory',
      icon: Icons.warehouse_outlined,
      selectedIcon: Icons.warehouse,
    ));
  }

  if (permissions.contains('sales:view')) {
    items.add(const MobileNavItem(
      branchIndex: MobileShellBranch.sales,
      label: 'Sales',
      icon: Icons.point_of_sale_outlined,
      selectedIcon: Icons.point_of_sale,
    ));
  }

  if (permissions.contains('brands:view')) {
    items.add(const MobileNavItem(
      branchIndex: MobileShellBranch.catalogue,
      label: 'Catalogue',
      icon: Icons.category_outlined,
      selectedIcon: Icons.category,
    ));
  }

  if (_hasMoreAccess(permissions)) {
    items.add(const MobileNavItem(
      branchIndex: MobileShellBranch.more,
      label: 'More',
      icon: Icons.more_horiz,
      selectedIcon: Icons.more_horiz,
    ));
  }

  items.add(const MobileNavItem(
    branchIndex: MobileShellBranch.settings,
    label: 'Settings',
    icon: Icons.settings_outlined,
    selectedIcon: Icons.settings,
  ));

  return items;
}

List<MobileNavItem> mobileNavItemsForUser(AuthUser? user) =>
    mobileNavItemsFor(effectivePermissions(user));

String defaultRouteForPermissions(List<String> permissions) {
  final items = mobileNavItemsFor(permissions);
  if (items.isEmpty) return '/login';
  if (isStockOnlyUser(permissions)) {
    return '/stock';
  }
  return '/dashboard';
}

String defaultRouteForUser(AuthUser? user) => defaultRouteForPermissions(effectivePermissions(user));

bool isShellPathAllowed(String path, List<String> permissions) {
  if (path.startsWith('/dashboard')) return permissions.contains('dashboard:view');
  if (path.startsWith('/stock')) return permissions.contains('inventory:view');
  if (path.startsWith('/inventory')) return permissions.contains('inventory:create');
  if (path.startsWith('/sales')) return canViewSalesModule(permissions);
  if (path.startsWith('/catalogue')) return canViewCatalogueModule(permissions);
  if (path.startsWith('/more/reports')) return permissions.contains('reports:view');
  if (path.startsWith('/more/notifications')) return permissions.contains('notifications:view');
  if (path.startsWith('/more/backup')) return canAccessBackupModule(permissions);
  if (path.startsWith('/more/tally')) return permissions.contains('tally:view_status');
  if (path.startsWith('/more/audit')) return permissions.contains('audit:view');
  if (path.startsWith('/settings/users')) return permissions.contains('users:view');
  if (path.startsWith('/settings/access-roles')) {
    return permissions.contains('settings:modify') && permissions.contains('users:view');
  }
  if (path.startsWith('/settings/tally')) return permissions.contains('tally:view_status');
  if (path.startsWith('/settings/audit')) return permissions.contains('audit:view');
  if (path.startsWith('/settings/backup')) return canAccessBackupModule(permissions);
  if (path.startsWith('/settings')) return true;
  if (path.startsWith('/more')) return _hasMoreAccess(permissions);
  return true;
}

int? firstAllowedBranchIndex(List<String> permissions) {
  final items = mobileNavItemsFor(permissions);
  if (items.isEmpty) return null;
  return items.first.branchIndex;
}

bool isBranchAllowedForPermissions(int branchIndex, List<String> permissions) {
  return mobileNavItemsFor(permissions).any((item) => item.branchIndex == branchIndex);
}
