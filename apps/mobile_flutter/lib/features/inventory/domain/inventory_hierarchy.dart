import '../../dashboard/domain/dashboard_models.dart';
import '../domain/inventory_models.dart';
import 'product_category.dart';

class BrandInventorySummary {
  const BrandInventorySummary({
    required this.brandId,
    required this.brandName,
    this.logoFilename,
    required this.totalUnits,
    required this.availableUnits,
    required this.soldUnits,
    required this.byLocation,
  });

  final int brandId;
  final String brandName;
  final String? logoFilename;
  final int totalUnits;
  final int availableUnits;
  final int soldUnits;
  final List<LocationCount> byLocation;
}

class LocationCount {
  const LocationCount({required this.locationId, required this.locationName, required this.count});

  final int locationId;
  final String locationName;
  final int count;
}

class ModelInventoryRow {
  const ModelInventoryRow({
    required this.model,
    required this.availableUnits,
    required this.soldUnits,
    required this.totalUnits,
    required this.isZeroStock,
    required this.specsLabel,
  });

  final ProductModel model;
  final int availableUnits;
  final int soldUnits;
  final int totalUnits;
  final bool isZeroStock;
  final String specsLabel;
}

List<BrandInventorySummary> buildBrandSummaries(
  List<Brand> brands,
  List<DistributionGroup> distributionByBrand,
  List<InventoryItem> items,
) {
  final distMap = {for (final row in distributionByBrand) row.id: row};

  return brands
      .where((brand) => brand.isActive)
      .map((brand) {
        final dist = distMap[brand.id.toString()];
        final brandItems = items.where((item) => item.brandId == brand.id && !item.isArchived).toList();
        final availableFromItems =
            brandItems.where((entry) => entry.status != InventoryStatus.sold).length;
        final soldFromItems = brandItems.where((entry) => entry.status == InventoryStatus.sold).length;
        final locationMap = <int, LocationCount>{};

        for (final item in brandItems.where((entry) => entry.status != InventoryStatus.sold)) {
          final existing = locationMap[item.currentLocationId];
          if (existing != null) {
            locationMap[item.currentLocationId] = LocationCount(
              locationId: existing.locationId,
              locationName: existing.locationName,
              count: existing.count + 1,
            );
          } else {
            locationMap[item.currentLocationId] = LocationCount(
              locationId: item.currentLocationId,
              locationName: item.currentLocationName,
              count: 1,
            );
          }
        }

        final byLocation = locationMap.values.toList()
          ..sort((a, b) => a.locationName.compareTo(b.locationName));

        return BrandInventorySummary(
          brandId: brand.id,
          brandName: brand.name,
          logoFilename: brand.logoFilename,
          totalUnits: brandItems.isNotEmpty ? brandItems.length : (dist?.total ?? 0),
          availableUnits: brandItems.isNotEmpty ? availableFromItems : (dist?.available ?? 0),
          soldUnits: brandItems.isNotEmpty ? soldFromItems : (dist?.sold ?? 0),
          byLocation: byLocation,
        );
      })
      .toList()
    ..sort((a, b) => a.brandName.compareTo(b.brandName));
}

({List<ModelInventoryRow> all, List<ModelInventoryRow> inStock, List<ModelInventoryRow> zeroStock}) buildModelRows(
  List<ProductModel> models,
  List<DistributionGroup> distributionByModel,
  int brandId,
  List<InventoryItem> items,
) {
  final distMap = {for (final row in distributionByModel) row.id: row};
  final brandModels = models.where((model) => model.brandId == brandId && model.status != 'archived');

  final rows = brandModels.map((model) {
    final dist = distMap[model.id];
    final modelItems = items.where((item) => item.productModelId == model.id && !item.isArchived);
    final availableFromItems =
        modelItems.where((entry) => entry.status != InventoryStatus.sold).length;
    final soldFromItems = modelItems.where((entry) => entry.status == InventoryStatus.sold).length;
    final availableUnits = modelItems.isNotEmpty ? availableFromItems : (dist?.available ?? 0);
    final soldUnits = modelItems.isNotEmpty ? soldFromItems : (dist?.sold ?? 0);
    final totalUnits = modelItems.isNotEmpty ? modelItems.length : (dist?.total ?? (availableUnits + soldUnits));
    return ModelInventoryRow(
      model: model,
      availableUnits: availableUnits,
      soldUnits: soldUnits,
      totalUnits: totalUnits,
      isZeroStock: availableUnits == 0 && totalUnits > 0,
      specsLabel: model.specsLabel,
    );
  }).toList()
    ..sort((a, b) => a.model.modelNumber.compareTo(b.model.modelNumber));

  return (
    all: rows,
    inStock: rows.where((row) => row.availableUnits > 0).toList(),
    zeroStock: rows.where((row) => row.isZeroStock).toList(),
  );
}

/// Inventory admin — all catalogue models for a brand, plus rows inferred from items.
List<ModelInventoryRow> buildInventoryModelRows(
  List<ProductModel> models,
  List<DistributionGroup> distributionByModel,
  int brandId,
  List<InventoryItem> items,
) {
  final built = buildModelRows(models, distributionByModel, brandId, items);
  final rowsById = {for (final row in built.all) row.model.id: row};

  final brandItems = items.where((item) => item.brandId == brandId && !item.isArchived);
  final grouped = <String, List<InventoryItem>>{};
  for (final item in brandItems) {
    grouped.putIfAbsent(item.productModelId, () => []).add(item);
  }

  for (final entry in grouped.entries) {
    if (rowsById.containsKey(entry.key)) continue;
    final catalogueModel = models.where((model) => model.id == entry.key).firstOrNull;
    rowsById[entry.key] = _modelRowFromItems(entry.value, catalogueModel, distributionByModel);
  }

  final rows = rowsById.values.toList()
    ..sort((a, b) => a.model.modelNumber.compareTo(b.model.modelNumber));
  return rows;
}

ModelInventoryRow _modelRowFromItems(
  List<InventoryItem> modelItems,
  ProductModel? catalogueModel,
  List<DistributionGroup> distributionByModel,
) {
  final distMap = {for (final row in distributionByModel) row.id: row};
  final sample = modelItems.first;
  final model = catalogueModel ?? productModelFromInventoryItem(sample);
  final dist = distMap[model.id];
  final availableFromItems =
      modelItems.where((entry) => entry.status != InventoryStatus.sold).length;
  final soldFromItems = modelItems.where((entry) => entry.status == InventoryStatus.sold).length;
  final availableUnits = modelItems.isNotEmpty ? availableFromItems : (dist?.available ?? 0);
  final soldUnits = modelItems.isNotEmpty ? soldFromItems : (dist?.sold ?? 0);
  final totalUnits = modelItems.isNotEmpty ? modelItems.length : (dist?.total ?? (availableUnits + soldUnits));
  return ModelInventoryRow(
    model: model,
    availableUnits: availableUnits,
    soldUnits: soldUnits,
    totalUnits: totalUnits,
    isZeroStock: availableUnits == 0 && totalUnits > 0,
    specsLabel: model.specsLabel,
  );
}

ProductModel productModelFromInventoryItem(InventoryItem item) {
  return ProductModel(
    id: item.productModelId,
    brandId: item.brandId,
    category: item.category,
    accessoryKind: item.accessoryKind,
    partNumber: item.partNumber,
    modelNumber: item.modelNumber,
    modelName: item.modelName,
    cpu: item.cpu,
    gpu: item.gpu,
    ramGb: item.ramGb,
    storageValue: item.storageValue,
    storageUnit: item.storageUnit,
    storageType: item.storageType,
    status: 'active',
  );
}

List<Brand> deriveBrandsFromInventoryData(
  List<InventoryItem> items,
  List<DistributionGroup> distributionByBrand,
) {
  final byId = <int, Brand>{};
  for (final group in distributionByBrand) {
    final id = int.tryParse(group.id);
    if (id != null) {
      byId[id] = Brand(id: id, name: group.name, isActive: true);
    }
  }
  for (final item in items) {
    byId.putIfAbsent(
      item.brandId,
      () => Brand(id: item.brandId, name: item.brandName, isActive: true),
    );
  }
  return byId.values.toList()..sort((a, b) => a.name.compareTo(b.name));
}

/// Builds brand rows from product model catalogue when the brands API is unavailable.
List<Brand> deriveBrandsFromProductModels(List<ProductModel> models) {
  final byId = <int, Brand>{};
  for (final model in models) {
    if (model.status == 'archived') continue;
    final name = model.brandName?.trim();
    if (name == null || name.isEmpty) continue;
    byId.putIfAbsent(
      model.brandId,
      () => Brand(id: model.brandId, name: name, isActive: true),
    );
  }
  return byId.values.toList()..sort((a, b) => a.name.compareTo(b.name));
}

/// Merges multiple brand lists — later sources override earlier ones (catalogue API last).
List<Brand> mergeBrandCatalogues(List<List<Brand>> sources) {
  final byId = <int, Brand>{};
  for (final list in sources) {
    for (final brand in list) {
      if (!brand.isActive) continue;
      final existing = byId[brand.id];
      if (existing == null) {
        byId[brand.id] = brand;
        continue;
      }
      byId[brand.id] = Brand(
        id: brand.id,
        name: brand.name.isNotEmpty ? brand.name : existing.name,
        isActive: true,
        logoFilename: brand.logoFilename ?? existing.logoFilename,
      );
    }
  }
  return byId.values.toList()..sort((a, b) => a.name.compareTo(b.name));
}

List<Location> deriveLocationsFromInventoryItems(List<InventoryItem> items) {
  final byId = <int, Location>{};
  for (final item in items) {
    byId.putIfAbsent(
      item.currentLocationId,
      () => Location(id: item.currentLocationId, name: item.currentLocationName, isActive: true),
    );
  }
  return byId.values.toList()..sort((a, b) => a.name.compareTo(b.name));
}

List<ProductModel> deriveProductModelsFromInventoryItems(List<InventoryItem> items) {
  final byId = <String, ProductModel>{};
  for (final item in items) {
    byId.putIfAbsent(item.productModelId, () => productModelFromInventoryItem(item));
  }
  return byId.values.toList()
    ..sort((a, b) => a.modelNumber.compareTo(b.modelNumber));
}

List<ModelInventoryRow> filterInventoryModels({
  required List<ProductModel> models,
  required List<DistributionGroup> distributionByModel,
  required int brandId,
  required List<InventoryItem> items,
  required String search,
  required HierarchySearchField searchField,
  required bool showZeroStock,
  ProductCategoryFilter productCategoryFilter = ProductCategoryFilter.all,
}) {
  var rows = buildInventoryModelRows(models, distributionByModel, brandId, items);
  if (!showZeroStock) {
    rows = rows.where((row) => row.availableUnits > 0).toList();
  }
  rows = rows.where((row) => matchesCategoryFilter(row.model, productCategoryFilter)).toList();
  if (search.trim().isEmpty) return rows;
  return rows
      .where(
        (row) => matchesModelSearch(
          row.model,
          search,
          searchField,
          items: items,
        ),
      )
      .toList();
}

bool matchesCategoryFilter(ProductModel model, ProductCategoryFilter filter) {
  if (filter == ProductCategoryFilter.all) return true;
  if (filter == ProductCategoryFilter.accessory) return model.isAccessory;
  return model.isLaptop;
}

enum HierarchySearchField { all, modelNumber, modelName, partNumber, gpu, cpu, serial, display }

bool matchesModelSearch(
  ProductModel model,
  String query,
  HierarchySearchField field, {
  List<InventoryItem> items = const [],
}) {
  final term = query.trim().toLowerCase();
  if (term.isEmpty) return true;

  final sampleSerial = items
      .where((item) => item.productModelId == model.id)
      .map((item) => item.serialNumber)
      .firstOrNull;

  bool contains(String? value) => value?.toLowerCase().contains(term) ?? false;

  return switch (field) {
    HierarchySearchField.modelNumber => contains(model.modelNumber),
    HierarchySearchField.modelName => contains(model.modelName),
    HierarchySearchField.partNumber => contains(model.partNumber),
    HierarchySearchField.gpu => contains(model.gpu),
    HierarchySearchField.cpu => contains(model.cpu),
    HierarchySearchField.display => contains(model.display),
    HierarchySearchField.serial => contains(sampleSerial),
    HierarchySearchField.all =>
      contains(model.modelNumber) ||
          contains(model.modelName) ||
          contains(model.partNumber) ||
          contains(model.gpu) ||
          contains(model.cpu) ||
          contains(model.display) ||
          contains(sampleSerial),
  };
}

bool matchesSerialSearch(InventoryItem item, String query, HierarchySearchField field) {
  final term = query.trim().toLowerCase();
  if (term.isEmpty) return true;
  if (field == HierarchySearchField.serial || field == HierarchySearchField.all) {
    return item.serialNumber.toLowerCase().contains(term);
  }
  return true;
}
