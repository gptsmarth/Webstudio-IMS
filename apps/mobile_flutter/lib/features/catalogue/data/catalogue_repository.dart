import '../../../core/constants/api_paths.dart';
import '../../../core/errors/api_exception.dart';
import '../../../core/network/api_client.dart';
import '../../dashboard/domain/dashboard_models.dart';
import '../../inventory/domain/inventory_models.dart';
import '../domain/catalogue_models.dart';

class CatalogueRepository {
  CatalogueRepository(this._api);

  final ApiClient _api;

  Future<List<CatalogueBrand>> listBrands() async {
    final items = <CatalogueBrand>[];
    var page = 1;
    var totalPages = 1;
    while (page <= totalPages) {
      final result = await _api.getPaginated(
        ApiPaths.brands,
        queryParameters: {'page': page, 'page_size': 100},
        itemParser: (json) => CatalogueBrand.fromJson(json! as Map<String, dynamic>),
      );
      items.addAll(result.items);
      totalPages = result.totalPages;
      page += 1;
    }
    return items;
  }

  Future<CatalogueBrand> createBrand(CreateBrandRequest request) async {
    return _api.post(
      ApiPaths.brands,
      data: request.toJson(),
      parser: (json) => CatalogueBrand.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<CatalogueBrand> updateBrand(int id, Map<String, dynamic> data) async {
    return _api.patch(
      '${ApiPaths.brands}/$id',
      data: data,
      parser: (json) => CatalogueBrand.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<void> deleteBrand(int id) async {
    await _api.delete<Object?>(
      '${ApiPaths.brands}/$id',
      parser: (_) => null,
    );
  }

  Future<List<CatalogueLocation>> listLocations() async {
    final items = <CatalogueLocation>[];
    var page = 1;
    var totalPages = 1;
    while (page <= totalPages) {
      final result = await _api.getPaginated(
        ApiPaths.locations,
        queryParameters: {'page': page, 'page_size': 100},
        itemParser: (json) => CatalogueLocation.fromJson(json! as Map<String, dynamic>),
      );
      items.addAll(result.items);
      totalPages = result.totalPages;
      page += 1;
    }
    return items;
  }

  Future<CatalogueLocation> createLocation(CreateLocationRequest request) async {
    return _api.post(
      ApiPaths.locations,
      data: request.toJson(),
      parser: (json) => CatalogueLocation.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<CatalogueLocation> updateLocation(int id, Map<String, dynamic> data) async {
    return _api.patch(
      '${ApiPaths.locations}/$id',
      data: data,
      parser: (json) => CatalogueLocation.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<LocationDeletePreview> getLocationDeletePreview(int id) async {
    return _api.get(
      '${ApiPaths.locations}/$id/delete-preview',
      parser: (json) => LocationDeletePreview.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<void> deleteLocation(int id, {int? transferToLocationId}) async {
    await _api.delete<Object?>(
      '${ApiPaths.locations}/$id',
      data: transferToLocationId != null ? {'transfer_to_location_id': transferToLocationId} : const {},
      parser: (_) => null,
    );
  }

  Future<List<ProductModel>> listProductModels({bool includeArchived = false}) async {
    final items = <ProductModel>[];
    var page = 1;
    var totalPages = 1;
    while (page <= totalPages) {
      final result = await _api.getPaginated(
        ApiPaths.productModels,
        queryParameters: {
          'page': page,
          'page_size': 100,
          if (!includeArchived) 'archived': false,
        },
        itemParser: (json) => ProductModel.fromJson(json! as Map<String, dynamic>),
      );
      items.addAll(result.items);
      totalPages = result.totalPages;
      page += 1;
    }
    return items;
  }

  Future<DashboardDistribution> getDistribution() async {
    return _api.get(
      ApiPaths.dashboardDistribution,
      parser: (json) => DashboardDistribution.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<ProductModel> createProductModel(Map<String, dynamic> data) async {
    return _api.post(
      ApiPaths.productModels,
      data: data,
      parser: (json) => ProductModel.fromJson(json! as Map<String, dynamic>),
    );
  }

  /// Create a product model, or return the existing one when brand+model_number
  /// already exists (409). Prevents add-inventory wizards from orphaning models
  /// when a prior create succeeded but the client timed out or retried.
  Future<ProductModel> createOrFindProductModel(Map<String, dynamic> data) async {
    try {
      return await createProductModel(data);
    } catch (error) {
      if (!isConflictError(error)) rethrow;
      final brandId = data['brand_id'];
      final modelNumber = (data['model_number'] as String?)?.trim().toLowerCase();
      if (brandId is! int || modelNumber == null || modelNumber.isEmpty) rethrow;
      final models = await listProductModels();
      ProductModel? existing;
      for (final model in models) {
        if (model.brandId == brandId &&
            model.modelNumber.trim().toLowerCase() == modelNumber) {
          existing = model;
          break;
        }
      }
      if (existing == null) rethrow;
      return existing;
    }
  }

  Future<ProductModel> getProductModel(String id) async {
    return _api.get(
      '${ApiPaths.productModels}/$id',
      parser: (json) => ProductModel.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<ProductModel> updateProductModel(String id, Map<String, dynamic> data) async {
    return _api.patch(
      '${ApiPaths.productModels}/$id',
      data: data,
      parser: (json) => ProductModel.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<void> deleteProductModel(String id) async {
    await _api.delete('${ApiPaths.productModels}/$id', parser: (_) => null);
  }

  Future<ProductModel> updateSellingPrice(String id, double? price) async {
    return _api.patch(
      '${ApiPaths.productModels}/$id/selling-price',
      data: {'selling_price': price},
      parser: (json) => ProductModel.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<Map<String, dynamic>> resolveProductImage(String modelId) async {
    return _api.post(
      ApiPaths.productModelResolveImage(modelId),
      data: const {},
      parser: (json) => Map<String, dynamic>.from(json! as Map),
    );
  }

  /// Triggers an immediate ASUS-only live price refresh for one model.
  /// Returns `true` if a background refresh was actually scheduled.
  Future<bool> refreshLivePrice(String modelId) async {
    final result = await _api.post(
      ApiPaths.productModelRefreshLivePrice(modelId),
      data: const {},
      parser: (json) => Map<String, dynamic>.from(json! as Map),
    );
    return result['scheduled'] as bool? ?? false;
  }

  /// Bulk "Update prices" trigger for every active ASUS model.
  /// Returns how many models were scheduled for a background refresh.
  Future<int> refreshAllLivePrices() async {
    final result = await _api.post(
      ApiPaths.productModelsRefreshLivePrices,
      data: const {},
      parser: (json) => Map<String, dynamic>.from(json! as Map),
    );
    return (result['scheduled'] as num?)?.toInt() ?? 0;
  }
}
