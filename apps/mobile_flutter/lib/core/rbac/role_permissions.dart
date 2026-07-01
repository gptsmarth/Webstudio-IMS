import 'package:flutter/foundation.dart';
import '../../features/auth/domain/auth_models.dart';
import 'dashboard_permissions.dart';

const _dashboardAll = [
  'dashboard:view',
  ...kDashboardWidgetPermissions,
];

const _dashboardSalesperson = [
  'dashboard:view',
  'dashboard:inventory_distribution',
  'dashboard:quick_actions',
  'dashboard:recent_transfers',
  'dashboard:store_status',
];

/// Mirrors backend `permissions.py` — used when `/auth/me` omits permissions on restore.
const Map<String, List<String>> kRolePermissions = {
  'main_admin': [
    'inventory:view',
    'inventory:create',
    'inventory:edit',
    'inventory:stock_edit',
    'inventory:transfer',
    'inventory:archive',
    'inventory:restore',
    'inventory:export',
    'sales:view',
    'sales:create',
    'sales:cancel',
    'sales:export',
    'reports:view',
    'reports:export',
    ..._dashboardAll,
    'brands:view',
    'brands:create',
    'brands:edit',
    'brands:archive',
    'product_models:view',
    'product_models:create',
    'product_models:edit',
    'product_models:archive',
    'product_models:selling_price:edit',
    'locations:view',
    'locations:create',
    'locations:edit',
    'locations:archive',
    'users:view',
    'users:create',
    'users:edit',
    'users:reset_password',
    'users:activate',
    'users:deactivate',
    'audit:view',
    'audit:export',
    'audit:lifecycle',
    'notifications:view',
    'notifications:manage',
    'settings:view',
    'settings:modify',
    'backup:view',
    'backup:manage',
    'restore:view',
    'restore:execute',
    'tally:view_status',
    'tally:configure',
    'tally:run_sync',
    'tally:retry_sync',
  ],
  'admin': [
    'inventory:view',
    'inventory:create',
    'inventory:edit',
    'inventory:stock_edit',
    'inventory:transfer',
    'inventory:archive',
    'inventory:restore',
    'inventory:export',
    'sales:view',
    'sales:create',
    'sales:cancel',
    'sales:export',
    'reports:view',
    'reports:export',
    ..._dashboardAll,
    'brands:view',
    'brands:create',
    'brands:edit',
    'brands:archive',
    'product_models:view',
    'product_models:create',
    'product_models:edit',
    'product_models:archive',
    'product_models:selling_price:edit',
    'locations:view',
    'locations:create',
    'locations:edit',
    'locations:archive',
    'audit:lifecycle',
    'notifications:view',
    'notifications:manage',
    'backup:view',
    'backup:manage',
    'restore:view',
    'restore:execute',
    'tally:view_status',
    'tally:run_sync',
    'tally:retry_sync',
  ],
  'salesperson': [
    'inventory:view',
    'inventory:transfer',
    'inventory:stock_edit',
    'sales:view',
    ..._dashboardSalesperson,
    'brands:view',
    'product_models:view',
    'product_models:edit',
    'product_models:selling_price:edit',
    'locations:view',
    'notifications:view',
    'settings:view',
    'audit:lifecycle',
  ],
};

List<String> effectivePermissions(AuthUser? user) {
  if (user == null) return const [];
  if (user.permissions.isNotEmpty) return user.permissions;
  return List<String>.from(kRolePermissions[user.role] ?? const []);
}

AuthUser withEffectivePermissions(AuthUser user) {
  final resolved = effectivePermissions(user);
  if (listEquals(resolved, user.permissions)) return user;
  return AuthUser(
    id: user.id,
    username: user.username,
    role: user.role,
    displayName: user.displayName,
    status: user.status,
    mustChangePassword: user.mustChangePassword,
    themePreference: user.themePreference,
    permissions: resolved,
    lastLoginAt: user.lastLoginAt,
    createdAt: user.createdAt,
  );
}
