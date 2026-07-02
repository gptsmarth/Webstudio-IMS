import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../../dashboard/domain/dashboard_models.dart';
import '../../inventory/domain/inventory_models.dart';
import '../data/catalogue_repository.dart';
import '../domain/catalogue_models.dart';

const cataloguePageSize = 25;

class CatalogueWorkspaceState {
  const CatalogueWorkspaceState({
    this.loading = false,
    this.error,
    this.tab = CatalogueTab.brands,
    this.brands = const [],
    this.locations = const [],
    this.models = const [],
    this.distribution,
    this.search = '',
    this.includeArchived = false,
    this.brandFilterId,
    this.locationTypeFilter,
    this.page = 1,
    this.brandSortField = BrandSortField.displayOrder,
    this.locationSortField = LocationSortField.name,
    this.sortAscending = true,
    this.actionInProgress = false,
  });

  final bool loading;
  final String? error;
  final CatalogueTab tab;
  final List<CatalogueBrand> brands;
  final List<CatalogueLocation> locations;
  final List<ProductModel> models;
  final DashboardDistribution? distribution;
  final String search;
  final bool includeArchived;
  final int? brandFilterId;
  final String? locationTypeFilter;
  final int page;
  final BrandSortField brandSortField;
  final LocationSortField locationSortField;
  final bool sortAscending;
  final bool actionInProgress;

  Map<int, int> get modelCountsByBrand {
    final counts = <int, int>{};
    for (final model in models) {
      counts[model.brandId] = (counts[model.brandId] ?? 0) + 1;
    }
    return counts;
  }

  Map<String, DistributionGroup> get stockByBrandId {
    final map = <String, DistributionGroup>{};
    for (final DistributionGroup row in distribution?.byBrand ?? const <DistributionGroup>[]) {
      map[row.id] = row;
    }
    return map;
  }

  Map<String, DistributionGroup> get stockByLocationId {
    final map = <String, DistributionGroup>{};
    for (final DistributionGroup row in distribution?.byLocation ?? const <DistributionGroup>[]) {
      map[row.id] = row;
    }
    return map;
  }

  List<CatalogueBrand> get visibleBrands {
    var rows = [...brands];
    if (brandFilterId != null) rows = rows.where((b) => b.id == brandFilterId).toList();
    rows = rows.where((b) => matchesCatalogueSearch(search, [b.name, b.shortName])).toList();
    final dir = sortAscending ? 1 : -1;
    rows.sort((a, b) {
      switch (brandSortField) {
        case BrandSortField.name:
          return a.name.compareTo(b.name) * dir;
        case BrandSortField.displayOrder:
          return (a.displayOrder - b.displayOrder) * dir;
        case BrandSortField.models:
          return ((modelCountsByBrand[a.id] ?? 0) - (modelCountsByBrand[b.id] ?? 0)) * dir;
        case BrandSortField.available:
          final aStock = stockByBrandId['${a.id}']?.available ?? 0;
          final bStock = stockByBrandId['${b.id}']?.available ?? 0;
          return (aStock - bStock) * dir;
      }
    });
    return rows;
  }

  List<CatalogueLocation> get visibleLocations {
    var rows = [...locations];
    if (locationTypeFilter != null) {
      rows = rows.where((l) => l.locationType == locationTypeFilter).toList();
    }
    rows = rows.where((l) => matchesCatalogueSearch(search, [l.name])).toList();
    final dir = sortAscending ? 1 : -1;
    rows.sort((a, b) {
      switch (locationSortField) {
        case LocationSortField.name:
          return a.name.compareTo(b.name) * dir;
        case LocationSortField.locationType:
          return a.locationType.compareTo(b.locationType) * dir;
        case LocationSortField.stock:
          final aStock = stockByLocationId['${a.id}']?.available ?? 0;
          final bStock = stockByLocationId['${b.id}']?.available ?? 0;
          return (aStock - bStock) * dir;
        case LocationSortField.capacity:
          final aCap = stockByLocationId['${a.id}']?.total ?? 0;
          final bCap = stockByLocationId['${b.id}']?.total ?? 0;
          return (aCap - bCap) * dir;
      }
    });
    return rows;
  }

  int get totalFilteredCount => tab == CatalogueTab.brands ? visibleBrands.length : visibleLocations.length;

  int get totalPages => (totalFilteredCount / cataloguePageSize).ceil().clamp(1, 9999);

  CatalogueWorkspaceState copyWith({
    bool? loading,
    String? error,
    CatalogueTab? tab,
    List<CatalogueBrand>? brands,
    List<CatalogueLocation>? locations,
    List<ProductModel>? models,
    DashboardDistribution? distribution,
    String? search,
    bool? includeArchived,
    int? brandFilterId,
    String? locationTypeFilter,
    int? page,
    BrandSortField? brandSortField,
    LocationSortField? locationSortField,
    bool? sortAscending,
    bool? actionInProgress,
    bool clearError = false,
    bool clearBrandFilter = false,
    bool clearLocationTypeFilter = false,
  }) {
    return CatalogueWorkspaceState(
      loading: loading ?? this.loading,
      error: clearError ? null : error ?? this.error,
      tab: tab ?? this.tab,
      brands: brands ?? this.brands,
      locations: locations ?? this.locations,
      models: models ?? this.models,
      distribution: distribution ?? this.distribution,
      search: search ?? this.search,
      includeArchived: includeArchived ?? this.includeArchived,
      brandFilterId: clearBrandFilter ? null : brandFilterId ?? this.brandFilterId,
      locationTypeFilter: clearLocationTypeFilter ? null : locationTypeFilter ?? this.locationTypeFilter,
      page: page ?? this.page,
      brandSortField: brandSortField ?? this.brandSortField,
      locationSortField: locationSortField ?? this.locationSortField,
      sortAscending: sortAscending ?? this.sortAscending,
      actionInProgress: actionInProgress ?? this.actionInProgress,
    );
  }
}

final catalogueRepositoryProvider = Provider<CatalogueRepository>((ref) {
  return CatalogueRepository(ref.watch(apiClientProvider));
});

final catalogueWorkspaceProvider =
    StateNotifierProvider<CatalogueWorkspaceController, CatalogueWorkspaceState>((ref) {
  return CatalogueWorkspaceController(ref);
});

class CatalogueWorkspaceController extends StateNotifier<CatalogueWorkspaceState> {
  CatalogueWorkspaceController(this._ref) : super(const CatalogueWorkspaceState());

  final Ref _ref;

  CatalogueRepository get _repo => _ref.read(catalogueRepositoryProvider);

  Future<void> load() async {
    state = state.copyWith(loading: true, clearError: true);
    try {
      final results = await Future.wait([
        _repo.listBrands(),
        _repo.listLocations(),
        _repo.listProductModels(includeArchived: false),
        _repo.getDistribution(),
      ]);
      state = state.copyWith(
        loading: false,
        brands: results[0] as List<CatalogueBrand>,
        locations: results[1] as List<CatalogueLocation>,
        models: results[2] as List<ProductModel>,
        distribution: results[3] as DashboardDistribution,
      );
    } catch (error) {
      state = state.copyWith(loading: false, error: error.toString());
    }
  }

  void setTab(CatalogueTab tab) => state = state.copyWith(tab: tab, page: 1);
  void setSearch(String value) => state = state.copyWith(search: value, page: 1);
  void setIncludeArchived(bool value) => state = state.copyWith(includeArchived: value, page: 1);
  void setPage(int page) => state = state.copyWith(page: page);

  void toggleBrandSort(BrandSortField field) => _toggleSort(
        field,
        state.brandSortField,
        (f) => state.copyWith(brandSortField: f as BrandSortField, page: 1),
      );

  void toggleLocationSort(LocationSortField field) => _toggleSort(
        field,
        state.locationSortField,
        (f) => state.copyWith(locationSortField: f as LocationSortField, page: 1),
      );

  void _toggleSort(Object field, Object current, CatalogueWorkspaceState Function(Object) apply) {
    if (field == current) {
      state = state.copyWith(sortAscending: !state.sortAscending, page: 1);
    } else {
      state = apply(field).copyWith(sortAscending: true, page: 1);
    }
  }

  Future<void> createBrand(String name) async {
    state = state.copyWith(actionInProgress: true, clearError: true);
    try {
      await _repo.createBrand(CreateBrandRequest(name: name));
      await load();
      state = state.copyWith(actionInProgress: false);
    } catch (error) {
      state = state.copyWith(actionInProgress: false, error: error.toString());
    }
  }

  Future<void> deleteBrand(int id) async {
    state = state.copyWith(actionInProgress: true, clearError: true);
    try {
      await _repo.deleteBrand(id);
      await load();
      state = state.copyWith(actionInProgress: false);
    } catch (error) {
      state = state.copyWith(actionInProgress: false, error: error.toString());
    }
  }

  Future<void> createLocation(String name, String locationType) async {
    state = state.copyWith(actionInProgress: true, clearError: true);
    try {
      await _repo.createLocation(CreateLocationRequest(name: name, locationType: locationType));
      await load();
      state = state.copyWith(actionInProgress: false);
    } catch (error) {
      state = state.copyWith(actionInProgress: false, error: error.toString());
    }
  }

  Future<void> deleteLocation(int id, {int? transferToLocationId}) async {
    state = state.copyWith(actionInProgress: true, clearError: true);
    try {
      await _repo.deleteLocation(id, transferToLocationId: transferToLocationId);
      await load();
      state = state.copyWith(actionInProgress: false);
    } catch (error) {
      state = state.copyWith(actionInProgress: false, error: error.toString());
    }
  }

  Future<void> updateBrand(int id, Map<String, dynamic> data) async {
    state = state.copyWith(actionInProgress: true, clearError: true);
    try {
      await _repo.updateBrand(id, data);
      await load();
      state = state.copyWith(actionInProgress: false);
    } catch (error) {
      state = state.copyWith(actionInProgress: false, error: error.toString());
    }
  }

  Future<void> updateLocation(int id, Map<String, dynamic> data) async {
    state = state.copyWith(actionInProgress: true, clearError: true);
    try {
      await _repo.updateLocation(id, data);
      await load();
      state = state.copyWith(actionInProgress: false);
    } catch (error) {
      state = state.copyWith(actionInProgress: false, error: error.toString());
    }
  }
}
