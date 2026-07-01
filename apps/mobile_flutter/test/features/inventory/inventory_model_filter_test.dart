import 'package:flutter_test/flutter_test.dart';

import 'package:webstudio_ims/features/dashboard/domain/dashboard_models.dart';
import 'package:webstudio_ims/features/inventory/domain/inventory_hierarchy.dart';
import 'package:webstudio_ims/features/inventory/domain/inventory_models.dart';

void main() {
  test('filterInventoryModels includes item-backed models missing from brand catalogue filter', () {
    const modelId = 'orphan-model';
    const items = [
      InventoryItem(
        id: '1',
        serialNumber: 'SN-ACER-1',
        productModelId: modelId,
        brandId: 5,
        brandName: 'Acer',
        modelNumber: 'NITRO-5',
        modelName: 'Acer Nitro 5',
        cpu: 'i5',
        ramGb: 16,
        storageValue: '512',
        storageUnit: 'GB',
        storageType: 'SSD',
        color: 'Black',
        currentLocationId: 1,
        currentLocationName: 'Warehouse',
        status: InventoryStatus.available,
        isArchived: false,
        createdAt: '2026-01-01',
        updatedAt: '2026-01-02',
      ),
    ];

    final rows = filterInventoryModels(
      models: const [],
      distributionByModel: const [],
      brandId: 5,
      items: items,
      search: '',
      searchField: HierarchySearchField.all,
      showZeroStock: false,
    );

    expect(rows, hasLength(1));
    expect(rows.first.model.modelNumber, 'NITRO-5');
    expect(rows.first.availableUnits, 1);
  });

  test('filterInventoryModels lists all catalogue models when showZeroStock is true', () {
    const models = [
      ProductModel(
        id: 'm-zero',
        brandId: 2,
        modelNumber: 'X1',
        modelName: 'Zero stock model',
        cpu: 'i3',
        ramGb: 8,
        storageValue: '256',
        storageUnit: 'GB',
        storageType: 'SSD',
        status: 'active',
      ),
    ];

    final rows = filterInventoryModels(
      models: models,
      distributionByModel: const [
        DistributionGroup(id: 'm-zero', name: 'Zero stock model', available: 0, sold: 0, total: 0),
      ],
      brandId: 2,
      items: const [],
      search: '',
      searchField: HierarchySearchField.all,
      showZeroStock: true,
    );

    expect(rows, hasLength(1));
    expect(rows.first.availableUnits, 0);
  });
}
