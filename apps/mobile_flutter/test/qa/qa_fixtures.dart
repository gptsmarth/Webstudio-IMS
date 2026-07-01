import 'package:webstudio_ims/features/dashboard/domain/dashboard_models.dart';
import 'package:webstudio_ims/features/inventory/domain/inventory_models.dart';

Brand qaBrand(int id) => Brand(id: id, name: 'Brand $id', isActive: true);

Location qaLocation(int id) => Location(id: id, name: 'Location $id', isActive: true);

ProductModel qaModel({required String id, required int brandId}) => ProductModel(
      id: id,
      brandId: brandId,
      modelNumber: 'MN-$id',
      modelName: 'Model $id',
      cpu: 'i5',
      ramGb: 16,
      storageValue: '512',
      storageUnit: 'GB',
      storageType: 'SSD',
      status: 'active',
    );

InventoryItem qaItem({
  required int index,
  required int brandId,
  required String modelId,
  required int locationId,
  InventoryStatus status = InventoryStatus.available,
}) {
  return InventoryItem(
    id: 'item-$index',
    serialNumber: 'SN-${index.toString().padLeft(6, '0')}',
    productModelId: modelId,
    brandId: brandId,
    brandName: 'Brand $brandId',
    modelNumber: 'MN-$modelId',
    modelName: 'Model $modelId',
    cpu: 'i5',
    ramGb: 16,
    storageValue: '512',
    storageUnit: 'GB',
    storageType: 'SSD',
    color: 'Black',
    currentLocationId: locationId,
    currentLocationName: 'Location $locationId',
    status: status,
    isArchived: false,
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-01T00:00:00Z',
  );
}

List<Brand> qaBrands(int count) => List.generate(count, (i) => qaBrand(i + 1));

List<InventoryItem> qaLargeInventory({
  int brandCount = 10,
  int modelsPerBrand = 5,
  int serialsPerModel = 20,
}) {
  final items = <InventoryItem>[];
  var index = 0;
  for (var brand = 1; brand <= brandCount; brand++) {
    for (var model = 1; model <= modelsPerBrand; model++) {
      final modelId = 'model-$brand-$model';
      for (var serial = 0; serial < serialsPerModel; serial++) {
        index += 1;
        items.add(
          qaItem(
            index: index,
            brandId: brand,
            modelId: modelId,
            locationId: (index % 5) + 1,
          ),
        );
      }
    }
  }
  return items;
}

List<DistributionGroup> qaDistributionForBrands(int brandCount) {
  return List.generate(
    brandCount,
    (i) => DistributionGroup(
      id: '${i + 1}',
      name: 'Brand ${i + 1}',
      available: 50,
      sold: 10,
      total: 60,
    ),
  );
}
