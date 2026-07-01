import 'package:flutter_test/flutter_test.dart';

import 'package:webstudio_ims/features/inventory/domain/inventory_hierarchy.dart';
import 'package:webstudio_ims/features/inventory/presentation/inventory_controller.dart';

void main() {
  test('inventory admin shows all catalogue brands including zero stock', () {
    const workspace = InventoryWorkspaceState(
      inventoryAdminMode: true,
      brandSummaries: [
        BrandInventorySummary(
          brandId: 1,
          brandName: 'ASUS',
          totalUnits: 0,
          availableUnits: 0,
          soldUnits: 0,
          byLocation: [],
        ),
        BrandInventorySummary(
          brandId: 2,
          brandName: 'Canon',
          totalUnits: 3,
          availableUnits: 2,
          soldUnits: 1,
          byLocation: [],
        ),
      ],
    );

    expect(workspace.visibleBrands.map((brand) => brand.brandName), ['ASUS', 'Canon']);
  });
}
