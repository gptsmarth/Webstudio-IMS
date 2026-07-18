import 'package:flutter_test/flutter_test.dart';

import 'package:webstudio_ims/features/dashboard/domain/dashboard_models.dart';
import 'package:webstudio_ims/features/inventory/domain/inventory_hierarchy.dart';
import 'package:webstudio_ims/features/inventory/domain/inventory_models.dart';

void main() {
  test('buildBrandSummaries aggregates location counts', () {
    final brands = [const Brand(id: 1, name: 'ASUS', isActive: true)];
    final distribution = [
      const DistributionGroup(
          id: '1', name: 'ASUS', available: 2, sold: 1, total: 3),
    ];
    final items = [
      const InventoryItem(
        id: '1',
        serialNumber: 'SN1',
        productModelId: 'm1',
        brandId: 1,
        brandName: 'ASUS',
        modelNumber: 'X1',
        modelName: 'Vivobook',
        cpu: 'i5',
        ramGb: 16,
        storageValue: '512',
        storageUnit: 'GB',
        storageType: 'SSD',
        color: 'Black',
        currentLocationId: 10,
        currentLocationName: 'Store A',
        status: InventoryStatus.available,
        isArchived: false,
        createdAt: '2026-01-01',
        updatedAt: '2026-01-02',
      ),
    ];

    final summaries = buildBrandSummaries(brands, distribution, items);
    expect(summaries, hasLength(1));
    expect(summaries.first.availableUnits, 1);
    expect(summaries.first.byLocation.first.locationName, 'Store A');
  });

  test(
      'buildModelRows counts available units from items when distribution is missing',
      () {
    const models = [
      ProductModel(
        id: 'm1',
        brandId: 1,
        modelNumber: 'X515',
        modelName: 'Vivobook 15',
        cpu: 'i5',
        ramGb: 16,
        storageValue: '512',
        storageUnit: 'GB',
        storageType: 'SSD',
        status: 'active',
      ),
    ];
    const items = [
      InventoryItem(
        id: '1',
        serialNumber: 'SN1',
        productModelId: 'm1',
        brandId: 1,
        brandName: 'ASUS',
        modelNumber: 'X515',
        modelName: 'Vivobook 15',
        cpu: 'i5',
        ramGb: 16,
        storageValue: '512',
        storageUnit: 'GB',
        storageType: 'SSD',
        color: 'Black',
        currentLocationId: 10,
        currentLocationName: 'Store A',
        status: InventoryStatus.available,
        isArchived: false,
        createdAt: '2026-01-01',
        updatedAt: '2026-01-02',
      ),
    ];

    final rows = buildModelRows(models, const [], 1, items);
    expect(rows.all, hasLength(1));
    expect(rows.inStock, hasLength(1));
    expect(rows.inStock.first.availableUnits, 1);
  });

  test('buildModelRows includes zero-stock catalogue models in all', () {
    const models = [
      ProductModel(
        id: 'm1',
        brandId: 1,
        modelNumber: 'X515',
        modelName: 'Vivobook 15',
        cpu: 'i5',
        ramGb: 16,
        storageValue: '512',
        storageUnit: 'GB',
        storageType: 'SSD',
        status: 'active',
      ),
      ProductModel(
        id: 'm2',
        brandId: 1,
        modelNumber: 'X999',
        modelName: 'Empty model',
        cpu: 'i5',
        ramGb: 8,
        storageValue: '256',
        storageUnit: 'GB',
        storageType: 'SSD',
        status: 'active',
      ),
    ];

    final rows = buildModelRows(models, const [], 1, const []);
    expect(rows.all, hasLength(2));
    expect(rows.inStock, isEmpty);
    expect(rows.all.where((r) => r.availableUnits == 0), hasLength(2));
  });

  test('deriveBrandsFromInventoryData builds brands without catalogue API', () {
    const items = [
      InventoryItem(
        id: '1',
        serialNumber: 'SN1',
        productModelId: 'm1',
        brandId: 1,
        brandName: 'ASUS',
        modelNumber: 'X515',
        modelName: 'Vivobook 15',
        cpu: 'i5',
        ramGb: 16,
        storageValue: '512',
        storageUnit: 'GB',
        storageType: 'SSD',
        color: 'Black',
        currentLocationId: 10,
        currentLocationName: 'Store A',
        status: InventoryStatus.available,
        isArchived: false,
        createdAt: '2026-01-01',
        updatedAt: '2026-01-02',
      ),
    ];
    const distribution = [
      DistributionGroup(
          id: '2', name: 'Lenovo', available: 1, sold: 0, total: 1),
    ];

    final brands = deriveBrandsFromInventoryData(items, distribution);
    expect(brands.map((b) => b.name), containsAll(['ASUS', 'Lenovo']));
  });

  test('deriveBrandsFromProductModels includes zero-stock catalogue brands',
      () {
    const models = [
      ProductModel(
        id: 'm1',
        brandId: 3,
        brandName: 'Acer',
        modelNumber: 'A1',
        modelName: 'Aspire',
        cpu: 'i5',
        ramGb: 8,
        storageValue: '256',
        storageUnit: 'GB',
        storageType: 'SSD',
        status: 'active',
      ),
      ProductModel(
        id: 'm2',
        brandId: 4,
        brandName: 'Canon',
        modelNumber: 'C1',
        modelName: 'Printer',
        cpu: 'n/a',
        ramGb: 0,
        storageValue: '0',
        storageUnit: 'GB',
        storageType: 'SSD',
        status: 'active',
      ),
    ];

    final brands = deriveBrandsFromProductModels(models);
    expect(brands.map((b) => b.name), containsAll(['Acer', 'Canon']));
  });

  test('mergeBrandCatalogues fills gaps and prefers later catalogue rows', () {
    final merged = mergeBrandCatalogues([
      [Brand(id: 1, name: 'ASUS', isActive: true)],
      [
        Brand(id: 1, name: 'ASUS', isActive: true, logoFilename: 'asus.svg'),
        Brand(id: 2, name: 'Acer', isActive: true),
      ],
    ]);
    expect(merged, hasLength(2));
    expect(merged.firstWhere((b) => b.id == 1).logoFilename, 'asus.svg');
    expect(merged.map((b) => b.name), contains('Acer'));
  });

  test('model search finds a normalized part of a composite model number', () {
    const model = ProductModel(
      id: 'composite',
      brandId: 1,
      modelNumber: 'FA506NCG-HN200WS / FA506NCS',
      modelName: 'TUF Gaming',
      cpu: 'Ryzen 7',
      ramGb: 16,
      storageValue: '512',
      storageUnit: 'GB',
      storageType: 'SSD',
      status: 'active',
    );

    expect(
      matchesModelSearch(
        model,
        'fa506ncg-hn200ws',
        HierarchySearchField.modelNumber,
      ),
      isTrue,
    );
  });
}
