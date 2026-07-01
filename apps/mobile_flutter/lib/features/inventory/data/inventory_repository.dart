import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/constants/api_paths.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/json_map.dart';
import '../../../shared/models/pagination.dart';
import '../domain/inventory_models.dart';

class InventoryRepository {
  InventoryRepository(this._api);

  final ApiClient _api;

  Future<List<InventoryItem>> fetchAllItems({bool includeArchived = false}) async {
    final items = <InventoryItem>[];
    var page = 1;
    var totalPages = 1;
    while (page <= totalPages) {
      final result = await listItems(
        filters: InventoryListFilters(includeArchived: includeArchived),
        page: page,
        pageSize: 100,
      );
      items.addAll(result.items);
      totalPages = result.totalPages;
      page += 1;
    }
    return items;
  }

  Future<PaginatedResult<InventoryItem>> listItems({
    InventoryListFilters filters = const InventoryListFilters(),
    int page = 1,
    int pageSize = 50,
  }) async {
    return _api.getPaginated(
      ApiPaths.inventory,
      queryParameters: filters.toQueryParams(page: page, pageSize: pageSize),
      itemParser: (json) => InventoryItem.fromJson(asJsonMap(json)),
    );
  }

  Future<InventoryItem> getItem(String id) async {
    return _api.get(
      '${ApiPaths.inventory}/$id',
      parser: (json) => InventoryItem.fromJson(asJsonMap(json)),
    );
  }

  Future<InventoryItem> getBySerial(String serial) async {
    return _api.get(
      '${ApiPaths.inventory}/by-serial/${Uri.encodeComponent(serial)}',
      parser: (json) => InventoryItem.fromJson(asJsonMap(json)),
    );
  }

  Future<InventoryItem> transferLocation(String id, int locationId) async {
    return _api.patch(
      '${ApiPaths.inventory}/$id/location',
      data: {'location_id': locationId},
      parser: (json) => InventoryItem.fromJson(asJsonMap(json)),
    );
  }

  Future<InventoryItem> markSold(String id, MarkSoldRequest request) async {
    final response = await _api.patch<Map<String, dynamic>>(
      '${ApiPaths.inventory}/$id/mark-sold',
      data: request.toJson(),
      parser: (json) => Map<String, dynamic>.from(json! as Map),
    );
    return InventoryItem.fromJson(asJsonMap(response['inventory']));
  }

  Future<InventoryItem> createItem(CreateInventoryItemRequest request) async {
    return _api.post(
      ApiPaths.inventory,
      data: request.toJson(),
      parser: (json) => InventoryItem.fromJson(asJsonMap(json)),
    );
  }

  Future<InventoryItem> updateItem(String id, Map<String, dynamic> data) async {
    return _api.patch(
      '${ApiPaths.inventory}/$id',
      data: data,
      parser: (json) => InventoryItem.fromJson(asJsonMap(json)),
    );
  }

  Future<void> archiveItem(String id) async {
    await _api.post('${ApiPaths.inventory}/$id/archive', data: const {}, parser: (_) => null);
  }

  Future<InventoryItem> restoreItem(String id) async {
    return _api.post(
      '${ApiPaths.inventory}/$id/restore',
      data: const {},
      parser: (json) => InventoryItem.fromJson(asJsonMap(json)),
    );
  }

  Future<bool> serialExists(String serial) async {
    try {
      await getBySerial(serial);
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<List<Brand>> listBrands() async {
    final items = <Brand>[];
    var page = 1;
    var totalPages = 1;
    while (page <= totalPages) {
      final result = await _api.getPaginated(
        ApiPaths.brands,
        queryParameters: {'page': page, 'page_size': 100},
        itemParser: (json) => Brand.fromJson(asJsonMap(json)),
      );
      items.addAll(result.items);
      totalPages = result.totalPages;
      page += 1;
    }
    if (items.isNotEmpty) return items;

    // Desktop parity — unpaged list when pagination returns nothing.
    return _api.get(
      ApiPaths.brands,
      parser: (json) {
        if (json is! List) return <Brand>[];
        return json.map((entry) => Brand.fromJson(asJsonMap(entry))).toList();
      },
    );
  }

  Future<List<Location>> listLocations() async {
    final result = await _api.getPaginated(
      ApiPaths.locations,
      queryParameters: {'page': 1, 'page_size': 100},
      itemParser: (json) => Location.fromJson(asJsonMap(json)),
    );
    return result.items.where((location) => location.isActive).toList();
  }

  Future<List<ProductModel>> listProductModels() async {
    final items = <ProductModel>[];
    var page = 1;
    var totalPages = 1;
    while (page <= totalPages) {
      final result = await _api.getPaginated(
        ApiPaths.productModels,
        queryParameters: {'page': page, 'page_size': 100, 'archived': false},
        itemParser: (json) => ProductModel.fromJson(asJsonMap(json)),
      );
      items.addAll(result.items);
      totalPages = result.totalPages;
      page += 1;
    }
    return items;
  }
}

final inventoryRepositoryProvider = Provider<InventoryRepository>((ref) {
  return InventoryRepository(ref.watch(apiClientProvider));
});
