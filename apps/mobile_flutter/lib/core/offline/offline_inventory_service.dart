import '../../features/dashboard/data/dashboard_repository.dart';
import '../../features/dashboard/domain/dashboard_models.dart';
import '../../features/inventory/data/inventory_repository.dart';
import '../../features/inventory/domain/inventory_hierarchy.dart';
import '../../features/inventory/domain/inventory_models.dart';
import '../network/json_map.dart';
import 'offline_cache_store.dart';
import 'offline_models.dart';

class OfflineInventoryService {
  OfflineInventoryService({
    required InventoryRepository inventory,
    required DashboardRepository dashboard,
    required OfflineCacheStore cache,
    required bool Function() isOnline,
  })  : _inventory = inventory,
        _dashboard = dashboard,
        _cache = cache,
        _isOnline = isOnline;

  final InventoryRepository _inventory;
  final DashboardRepository _dashboard;
  final OfflineCacheStore _cache;
  final bool Function() _isOnline;

  Future<OfflineLoadResult<InventoryWorkspaceCache>> loadWorkspace({bool forceRefresh = false}) async {
    if (_isOnline() && forceRefresh) {
      try {
        final fresh = await _fetchAndCache();
        return OfflineLoadResult(data: fresh, fromCache: false, isStale: false);
      } catch (error) {
        final cached = _readWorkspaceCache();
        if (cached != null) {
          return OfflineLoadResult(
            data: cached,
            fromCache: true,
            isStale: true,
            error: error.toString(),
          );
        }
        rethrow;
      }
    }

    if (_isOnline()) {
      try {
        final fresh = await _fetchAndCache();
        return OfflineLoadResult(data: fresh, fromCache: false, isStale: false);
      } catch (_) {
        final cached = _readWorkspaceCache();
        if (cached != null) {
          return OfflineLoadResult(data: cached, fromCache: true, isStale: true);
        }
        rethrow;
      }
    }

    final cached = _readWorkspaceCache();
    if (cached == null) {
      throw StateError('No cached inventory data available offline.');
    }
    return OfflineLoadResult(data: cached, fromCache: true, isStale: true);
  }

  Future<OfflineLoadResult<InventoryItem?>> lookupBySerial(String serial) async {
    final normalized = serial.trim().toLowerCase();
    final cachedItems = _cache.readList(OfflineCacheKeys.inventoryItems);
    if (cachedItems != null) {
      for (final row in cachedItems.data) {
        final value = row['serial_number']?.toString().toLowerCase();
        if (value == normalized) {
          return OfflineLoadResult(
            data: InventoryItem.fromJson(asJsonMap(row)),
            fromCache: true,
            isStale: _isOnline(),
          );
        }
      }
    }

    if (!_isOnline()) {
      return const OfflineLoadResult(data: null, fromCache: true, isStale: true);
    }

    try {
      final item = await _inventory.getBySerial(serial);
      await _upsertCachedItem(item);
      return OfflineLoadResult(data: item, fromCache: false, isStale: false);
    } catch (_) {
      return const OfflineLoadResult(data: null, fromCache: false, isStale: false);
    }
  }

  Future<void> cacheWorkspace({
    required List<Brand> brands,
    required List<ProductModel> models,
    required List<Location> locations,
    required DashboardDistribution distribution,
    required List<InventoryItem> items,
  }) async {
    await _cache.putList(
      OfflineCacheKeys.inventoryBrands,
      brands.map((b) => {'id': b.id, 'name': b.name, 'is_active': b.isActive, 'logo_filename': b.logoFilename}).toList(),
    );
    await _cache.putList(
      OfflineCacheKeys.inventoryModels,
      models
          .map((m) => {
                'id': m.id,
                'brand_id': m.brandId,
                'model_number': m.modelNumber,
                'model_name': m.modelName,
                'cpu': m.cpu,
                'gpu': m.gpu,
                'ram_gb': m.ramGb,
                'storage_value': m.storageValue,
                'storage_unit': m.storageUnit,
                'storage_type': m.storageType,
                'display': m.display,
                'status': m.status,
                'product_image_url': m.productImageUrl,
              })
          .toList(),
    );
    await _cache.putList(
      OfflineCacheKeys.inventoryLocations,
      locations.map((l) => {'id': l.id, 'name': l.name, 'is_active': l.isActive}).toList(),
    );
    await _cache.putMap(OfflineCacheKeys.inventoryDistribution, _distributionToJson(distribution));
    await _cache.putList(OfflineCacheKeys.inventoryItems, items.map((item) => item.toJson()).toList());
  }

  Future<InventoryWorkspaceCache> _fetchAndCache() async {
    // Fetch the heavy lists concurrently — sequential waits were stacking into
    // multi-minute UI freezes after every transfer/sale refresh on Android.
    final distributionFuture = _dashboard.getDistribution();
    final itemsFuture = _inventory.fetchAllItems();
    final modelsFuture = () async {
      try {
        return await _inventory.listProductModels();
      } catch (_) {
        return <ProductModel>[];
      }
    }();
    final locationsFuture = () async {
      try {
        return await _inventory.listLocations();
      } catch (_) {
        return <Location>[];
      }
    }();

    final distribution = await distributionFuture;
    final items = await itemsFuture;
    var models = await modelsFuture;
    if (models.isEmpty) {
      models = deriveProductModelsFromInventoryItems(items);
    }
    var locations = await locationsFuture;
    if (locations.isEmpty) {
      locations = deriveLocationsFromInventoryItems(items);
    }

    final brands = await _loadBrandCatalogue(
      items: items,
      models: models,
      distributionByBrand: distribution.byBrand,
    );

    final workspace = InventoryWorkspaceCache(
      brands: brands,
      models: models,
      locations: locations,
      distribution: distribution,
      items: items,
    );
    await cacheWorkspace(
      brands: workspace.brands,
      models: workspace.models,
      locations: workspace.locations,
      distribution: workspace.distribution,
      items: workspace.items,
    );
    return workspace;
  }

  Future<List<Brand>> _loadBrandCatalogue({
    required List<InventoryItem> items,
    required List<ProductModel> models,
    required List<DistributionGroup> distributionByBrand,
  }) async {
    final sources = <List<Brand>>[];

    try {
      final catalogueBrands = await _inventory.listBrands();
      if (catalogueBrands.isNotEmpty) {
        sources.add(catalogueBrands);
      }
    } catch (_) {
      // Fall through to derived catalogues below.
    }

    final fromModels = deriveBrandsFromProductModels(models);
    if (fromModels.isNotEmpty) {
      sources.add(fromModels);
    }

    final fromInventory = deriveBrandsFromInventoryData(items, distributionByBrand);
    if (fromInventory.isNotEmpty) {
      sources.add(fromInventory);
    }

    if (sources.isEmpty) return const [];
    return mergeBrandCatalogues(sources);
  }

  InventoryWorkspaceCache? _readWorkspaceCache() {
    final brandsRaw = _cache.readList(OfflineCacheKeys.inventoryBrands);
    final modelsRaw = _cache.readList(OfflineCacheKeys.inventoryModels);
    final locationsRaw = _cache.readList(OfflineCacheKeys.inventoryLocations);
    final distributionRaw = _cache.readMap(OfflineCacheKeys.inventoryDistribution);
    final itemsRaw = _cache.readList(OfflineCacheKeys.inventoryItems);
    if (brandsRaw == null || modelsRaw == null || locationsRaw == null || distributionRaw == null || itemsRaw == null) {
      return null;
    }
    return InventoryWorkspaceCache(
      brands: brandsRaw.data.map((json) => Brand.fromJson(json)).toList(),
      models: modelsRaw.data.map((json) => ProductModel.fromJson(json)).toList(),
      locations: locationsRaw.data.map((json) => Location.fromJson(json)).toList(),
      distribution: DashboardDistribution.fromJson(distributionRaw.data),
      items: itemsRaw.data.map((json) => InventoryItem.fromJson(json)).toList(),
    );
  }

  Future<void> _upsertCachedItem(InventoryItem item) async {
    final cached = _cache.readList(OfflineCacheKeys.inventoryItems);
    final rows = cached?.data.toList() ?? <Map<String, dynamic>>[];
    final index = rows.indexWhere((row) => row['id'] == item.id);
    final json = item.toJson();
    if (index >= 0) {
      rows[index] = json;
    } else {
      rows.add(json);
    }
    await _cache.putList(OfflineCacheKeys.inventoryItems, rows);
  }

  Map<String, dynamic> _distributionToJson(DashboardDistribution distribution) => {
        'total_available_inventory': distribution.totalAvailableInventory,
        'by_brand': distribution.byBrand
            .map((g) => {'id': g.id, 'name': g.name, 'available': g.available, 'sold': g.sold, 'total': g.total})
            .toList(),
        'by_location': distribution.byLocation
            .map((g) => {'id': g.id, 'name': g.name, 'available': g.available, 'sold': g.sold, 'total': g.total})
            .toList(),
        'by_product_model': distribution.byProductModel
            .map((g) => {'id': g.id, 'name': g.name, 'available': g.available, 'sold': g.sold, 'total': g.total})
            .toList(),
        'as_of': distribution.asOf,
      };
}

class InventoryWorkspaceCache {
  const InventoryWorkspaceCache({
    required this.brands,
    required this.models,
    required this.locations,
    required this.distribution,
    required this.items,
  });

  final List<Brand> brands;
  final List<ProductModel> models;
  final List<Location> locations;
  final DashboardDistribution distribution;
  final List<InventoryItem> items;
}
