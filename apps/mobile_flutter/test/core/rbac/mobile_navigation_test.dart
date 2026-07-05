import 'package:flutter_test/flutter_test.dart';

import 'package:webstudio_ims/core/rbac/mobile_navigation.dart';
import 'package:webstudio_ims/core/rbac/role_permissions.dart';
import 'package:webstudio_ims/features/auth/domain/auth_models.dart';

void main() {
  const salesperson = AuthUser(
    id: 2,
    username: 'arvind',
    role: 'salesperson',
    permissions: const [],
  );

  const admin = AuthUser(
    id: 1,
    username: 'admin',
    role: 'admin',
    permissions: const [],
  );

  test('effectivePermissions falls back to role when list is empty', () {
    expect(effectivePermissions(salesperson), contains('inventory:view'));
    expect(effectivePermissions(salesperson), contains('product_models:edit'));
    expect(effectivePermissions(salesperson), isNot(contains('inventory:create')));
    expect(effectivePermissions(admin), containsAll(['inventory:view', 'inventory:create']));
  });

  test('salesperson nav follows granted permissions', () {
    final items = mobileNavItemsForUser(salesperson);
    expect(items.map((item) => item.label).toList(), ['Dashboard', 'Stock', 'Sales', 'Catalogue', 'More', 'Settings']);
    expect(defaultRouteForUser(salesperson), '/stock');
  });

  test('admin nav includes stock and inventory', () {
    final items = mobileNavItemsForUser(admin);
    final labels = items.map((item) => item.label).toList();
    expect(labels, contains('Stock'));
    expect(labels, contains('Inventory'));
    expect(labels, contains('Sales'));
    expect(labels, contains('Settings'));
    final inventory = items.firstWhere((item) => item.label == 'Inventory');
    expect(inventory.shortLabel, 'Add');
  });

  test('isShellPathAllowed blocks inventory create route without permission', () {
    final perms = effectivePermissions(salesperson);
    expect(isShellPathAllowed('/stock', perms), isTrue);
    expect(isShellPathAllowed('/inventory', perms), isFalse);
    expect(isShellPathAllowed('/sales', perms), isTrue);
    expect(isShellPathAllowed('/settings', perms), isTrue);
  });

  test('salesperson can edit stock product models', () {
    final perms = effectivePermissions(salesperson);
    expect(canEditStockProductModel(perms), isTrue);
    expect(canEditStockLaptop(perms), isTrue);
    expect(canEditProductModels(perms), isTrue);
  });

  test('stock edit permission alone enables stock model editing', () {
    const perms = ['inventory:view', 'inventory:stock_edit'];
    expect(canEditStockProductModel(perms), isTrue);
    expect(canEditProductModels(perms), isFalse);
  });
}
