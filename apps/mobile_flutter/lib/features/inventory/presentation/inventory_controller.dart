import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/api_exception.dart';
import '../../../core/offline/offline_dashboard_service.dart';
import '../../../core/offline/offline_models.dart';
import '../../../core/offline/offline_providers.dart';
import '../../../core/offline/offline_inventory_service.dart';
import '../../../core/offline/pending_operation_factory.dart';
import '../data/stock_show_price_preferences.dart';
import '../../catalogue/domain/catalogue_models.dart';
import '../../catalogue/presentation/catalogue_controller.dart';
import '../../dashboard/domain/dashboard_models.dart';
import '../data/inventory_repository.dart';
import '../domain/inventory_hierarchy.dart';
import '../domain/inventory_models.dart';
import '../domain/product_category.dart';
import '../domain/product_spec_lookup.dart';

enum InventoryNavLevel { brands, models, serials }

class InventoryWorkspaceState {
  const InventoryWorkspaceState({
    this.loading = false,
    this.error,
    this.brands = const [],
    this.models = const [],
    this.locations = const [],
    this.items = const [],
    this.distribution,
    this.brandSummaries = const [],
    this.navLevel = InventoryNavLevel.brands,
    this.selectedBrandId,
    this.selectedModelId,
    this.search = '',
    this.searchField = HierarchySearchField.all,
    this.filters = const InventoryListFilters(),
    this.selectedItem,
    this.actionInProgress = false,
    this.includeZeroStock = false,
    this.inventoryAdminMode = false,
    this.showZeroStock = false,
    this.showSellingPrice = false,
    this.showLivePrice = false,
    this.asusPriceRunStatus,
    this.asusPriceRunDismissedAt,
    this.asusPriceRunStarting = false,
    this.asusPriceRunRetrying = false,
    this.productCategoryFilter = ProductCategoryFilter.all,
    this.fromCache = false,
    this.isStale = false,
  });

  final bool loading;
  final String? error;
  final List<Brand> brands;
  final List<ProductModel> models;
  final List<Location> locations;
  final List<InventoryItem> items;
  final DashboardDistribution? distribution;
  final List<BrandInventorySummary> brandSummaries;
  final InventoryNavLevel navLevel;
  final int? selectedBrandId;
  final String? selectedModelId;
  final String search;
  final HierarchySearchField searchField;
  final InventoryListFilters filters;
  final InventoryItem? selectedItem;
  final bool actionInProgress;
  final bool includeZeroStock;
  final bool inventoryAdminMode;
  final bool showZeroStock;
  final bool showSellingPrice;
  final bool showLivePrice;
  final AsusPriceRefreshStatus? asusPriceRunStatus;
  final String? asusPriceRunDismissedAt;
  final bool asusPriceRunStarting;
  final bool asusPriceRunRetrying;
  final ProductCategoryFilter productCategoryFilter;

  bool get _asusPriceRunFinished {
    final status = asusPriceRunStatus;
    return status != null &&
        status.total > 0 &&
        status.inProgress == 0 &&
        status.finishedAt != null;
  }

  /// True only while there's a completed, undismissed bulk run to show —
  /// mirrors desktop's "Done — refreshed N ASUS model(s)." banner + dismiss.
  bool get asusPriceRunShowsDismiss {
    if (!_asusPriceRunFinished) return false;
    return asusPriceRunStatus!.finishedAt != asusPriceRunDismissedAt;
  }

  /// "Retry failed" stays available even after the banner is dismissed —
  /// dismissing only clears the summary text, not the ability to go fix the
  /// models that didn't resolve.
  bool get asusPriceRunShowsRetry =>
      _asusPriceRunFinished && asusPriceRunStatus!.failedModelIds.isNotEmpty;

  String? get asusPriceRunMessage {
    final status = asusPriceRunStatus;
    if (status == null || status.total == 0) return null;
    if (status.inProgress > 0) {
      return 'Refreshing ASUS prices — ${status.completed} of ${status.total} done…';
    }
    if (asusPriceRunShowsDismiss) {
      final failedCount = status.failedModelIds.length;
      if (failedCount > 0) {
        final okCount = status.total - failedCount;
        return 'Done — $okCount of ${status.total} updated, $failedCount not found.';
      }
      return 'Done — refreshed ${status.total} ASUS model(s).';
    }
    return null;
  }
  final bool fromCache;
  final bool isStale;

  Brand? get selectedBrand {
    if (selectedBrandId == null) return null;
    for (final brand in brands) {
      if (brand.id == selectedBrandId) return brand;
    }
    return null;
  }

  ProductModel? get selectedModel {
    if (selectedModelId == null) return null;
    for (final model in models) {
      if (model.id == selectedModelId) return model;
    }
    return null;
  }

  List<BrandInventorySummary> get visibleBrands {
    if (search.trim().isEmpty) return brandSummaries;
    final term = search.toLowerCase();
    return brandSummaries.where((brand) => brand.brandName.toLowerCase().contains(term)).toList();
  }

  List<ModelInventoryRow> get visibleModels {
    if (selectedBrandId == null) return [];
    List<ModelInventoryRow> rows;
    if (inventoryAdminMode) {
      rows = filterInventoryModels(
        models: models,
        distributionByModel: distribution?.byProductModel ?? [],
        brandId: selectedBrandId!,
        items: items,
        search: search,
        searchField: searchField,
        showZeroStock: showZeroStock,
        productCategoryFilter: productCategoryFilter,
      );
    } else {
      final built = buildModelRows(
        models,
        distribution?.byProductModel ?? [],
        selectedBrandId!,
        items,
      );
      rows = built.inStock;
      if (productCategoryFilter != ProductCategoryFilter.all) {
        rows = rows.where((row) => matchesCategoryFilter(row.model, productCategoryFilter)).toList();
      }
      if (search.trim().isNotEmpty) {
        rows = rows
            .where((row) => matchesModelSearch(row.model, search, searchField, items: items))
            .toList();
      }
    }
    return rows;
  }

  BrandInventorySummary? get selectedBrandSummary {
    if (selectedBrandId == null) return null;
    for (final summary in brandSummaries) {
      if (summary.brandId == selectedBrandId) return summary;
    }
    return null;
  }

  List<InventoryItem> get availableUnitsForSelectedModel {
    if (selectedModelId == null) return [];
    return items
        .where((item) =>
            item.productModelId == selectedModelId &&
            !item.isArchived &&
            item.status != InventoryStatus.sold)
        .toList()
      ..sort((a, b) => a.serialNumber.compareTo(b.serialNumber));
  }

  /// Inventory admin — all non-archived serials for the selected model (includes sold).
  List<InventoryItem> get serialUnitsForSelectedModel {
    if (selectedModelId == null) return [];
    return items
        .where((item) => item.productModelId == selectedModelId && !item.isArchived)
        .toList()
      ..sort((a, b) => a.serialNumber.compareTo(b.serialNumber));
  }

  List<InventoryItem> get visibleSerials {
    if (selectedModelId == null) return [];
    var pool = items.where((item) => item.productModelId == selectedModelId && !item.isArchived);
    if (filters.status == null) {
      pool = pool.where((item) => item.status != InventoryStatus.sold);
    }
    if (filters.status != null) {
      pool = pool.where((item) => item.status == filters.status);
    }
    if (filters.currentLocationId != null) {
      pool = pool.where((item) => item.currentLocationId == filters.currentLocationId);
    }
    if (filters.color != null && filters.color!.trim().isNotEmpty) {
      final color = filters.color!.toLowerCase();
      pool = pool.where((item) => item.color.toLowerCase().contains(color));
    }
    if (search.trim().isNotEmpty) {
      pool = pool.where((item) => matchesSerialSearch(item, search, searchField));
    }
    return pool.toList()
      ..sort((a, b) => a.serialNumber.compareTo(b.serialNumber));
  }

  InventoryWorkspaceState copyWith({
    bool? loading,
    String? error,
    List<Brand>? brands,
    List<ProductModel>? models,
    List<Location>? locations,
    List<InventoryItem>? items,
    DashboardDistribution? distribution,
    List<BrandInventorySummary>? brandSummaries,
    InventoryNavLevel? navLevel,
    int? selectedBrandId,
    String? selectedModelId,
    String? search,
    HierarchySearchField? searchField,
    InventoryListFilters? filters,
    InventoryItem? selectedItem,
    bool? actionInProgress,
    bool? includeZeroStock,
    bool? inventoryAdminMode,
    bool? showZeroStock,
    bool? showSellingPrice,
    bool? showLivePrice,
    AsusPriceRefreshStatus? asusPriceRunStatus,
    String? asusPriceRunDismissedAt,
    bool? asusPriceRunStarting,
    bool? asusPriceRunRetrying,
    ProductCategoryFilter? productCategoryFilter,
    bool? fromCache,
    bool? isStale,
    bool clearError = false,
    bool clearSelection = false,
  }) {
    return InventoryWorkspaceState(
      loading: loading ?? this.loading,
      error: clearError ? null : error ?? this.error,
      brands: brands ?? this.brands,
      models: models ?? this.models,
      locations: locations ?? this.locations,
      items: items ?? this.items,
      distribution: distribution ?? this.distribution,
      brandSummaries: brandSummaries ?? this.brandSummaries,
      navLevel: navLevel ?? this.navLevel,
      selectedBrandId: selectedBrandId ?? this.selectedBrandId,
      selectedModelId: selectedModelId ?? this.selectedModelId,
      search: search ?? this.search,
      searchField: searchField ?? this.searchField,
      filters: filters ?? this.filters,
      selectedItem: clearSelection ? null : selectedItem ?? this.selectedItem,
      actionInProgress: actionInProgress ?? this.actionInProgress,
      includeZeroStock: includeZeroStock ?? this.includeZeroStock,
      inventoryAdminMode: inventoryAdminMode ?? this.inventoryAdminMode,
      showZeroStock: showZeroStock ?? this.showZeroStock,
      showSellingPrice: showSellingPrice ?? this.showSellingPrice,
      showLivePrice: showLivePrice ?? this.showLivePrice,
      asusPriceRunStatus: asusPriceRunStatus ?? this.asusPriceRunStatus,
      asusPriceRunDismissedAt: asusPriceRunDismissedAt ?? this.asusPriceRunDismissedAt,
      asusPriceRunStarting: asusPriceRunStarting ?? this.asusPriceRunStarting,
      asusPriceRunRetrying: asusPriceRunRetrying ?? this.asusPriceRunRetrying,
      productCategoryFilter: productCategoryFilter ?? this.productCategoryFilter,
      fromCache: fromCache ?? this.fromCache,
      isStale: isStale ?? this.isStale,
    );
  }
}

typedef InventoryWorkspaceProvider =
    StateNotifierProvider<InventoryWorkspaceController, InventoryWorkspaceState>;

final stockWorkspaceProvider =
    StateNotifierProvider<InventoryWorkspaceController, InventoryWorkspaceState>((ref) {
  final controller = InventoryWorkspaceController(ref);
  ref.onDispose(controller.dispose);
  return controller;
});

final inventoryAdminWorkspaceProvider =
    StateNotifierProvider<InventoryWorkspaceController, InventoryWorkspaceState>((ref) {
  final controller = InventoryWorkspaceController(ref, inventoryAdminMode: true);
  ref.onDispose(controller.dispose);
  return controller;
});

/// Admin inventory mutations (add laptop, global search → inventory).
final inventoryWorkspaceProvider = inventoryAdminWorkspaceProvider;

class InventoryWorkspaceController extends StateNotifier<InventoryWorkspaceState> {
  InventoryWorkspaceController(this._ref, {bool inventoryAdminMode = false})
      : _inventoryAdminMode = inventoryAdminMode,
        super(InventoryWorkspaceState(inventoryAdminMode: inventoryAdminMode));

  final Ref _ref;
  final bool _inventoryAdminMode;
  bool _pricePreferenceLoaded = false;
  final ScrollController brandsScrollController = ScrollController();
  final ScrollController modelsScrollController = ScrollController();
  Timer? _asusPricePollTimer;
  String? _asusPriceRunRefreshedForFinishedAt;
  static const _asusPricePollInterval = Duration(seconds: 4);

  void dispose() {
    brandsScrollController.dispose();
    modelsScrollController.dispose();
    _asusPricePollTimer?.cancel();
    super.dispose();
  }

  InventoryRepository get _inventory => _ref.read(inventoryRepositoryProvider);
  OfflineInventoryService get _offlineInventory => _ref.read(offlineInventoryServiceProvider);
  bool get _isOnline => _ref.read(networkStatusProvider);

  Future<void> load() async {
    await _ensurePricePreferenceLoaded();
    state = state.copyWith(loading: true, clearError: true);
    try {
      final result = await _offlineInventory.loadWorkspace(forceRefresh: _isOnline);
      final workspace = result.data;
      state = state.copyWith(
        loading: false,
        brands: workspace.brands,
        models: workspace.models,
        locations: workspace.locations,
        distribution: workspace.distribution,
        items: workspace.items,
        brandSummaries: buildBrandSummaries(workspace.brands, workspace.distribution.byBrand, workspace.items),
        fromCache: result.fromCache,
        isStale: result.isStale,
      );
    } catch (error) {
      state = state.copyWith(loading: false, error: error.toString());
    }
  }

  void selectBrand(int brandId) {
    state = state.copyWith(
      selectedBrandId: brandId,
      selectedModelId: null,
      navLevel: InventoryNavLevel.models,
      search: '',
      searchField: HierarchySearchField.all,
      clearSelection: true,
    );
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (modelsScrollController.hasClients) {
        modelsScrollController.jumpTo(0);
      }
    });
    if (!_inventoryAdminMode && state.selectedBrand?.name.trim().toUpperCase() == 'ASUS') {
      unawaited(syncAsusPriceRunStatus());
    } else {
      _asusPricePollTimer?.cancel();
      _asusPricePollTimer = null;
    }
  }

  void selectModel(String modelId) {
    state = state.copyWith(
      selectedModelId: modelId,
      navLevel: InventoryNavLevel.serials,
      search: '',
      clearSelection: true,
    );
  }

  void goBack() {
    switch (state.navLevel) {
      case InventoryNavLevel.serials:
        state = state.copyWith(navLevel: InventoryNavLevel.models, selectedModelId: null, clearSelection: true);
      case InventoryNavLevel.models:
        state = state.copyWith(navLevel: InventoryNavLevel.brands, selectedBrandId: null, clearSelection: true);
        _asusPricePollTimer?.cancel();
        _asusPricePollTimer = null;
        if (_isOnline) {
          unawaited(_refreshItemsInBackground());
        }
      case InventoryNavLevel.brands:
        break;
    }
  }

  void setSearch(String value) => state = state.copyWith(search: value);
  void setSearchField(HierarchySearchField field) => state = state.copyWith(searchField: field);
  void setFilters(InventoryListFilters filters) => state = state.copyWith(filters: filters);
  void setIncludeZeroStock(bool value) => state = state.copyWith(includeZeroStock: value);
  void setShowZeroStock(bool value) => state = state.copyWith(showZeroStock: value);

  void setProductCategoryFilter(ProductCategoryFilter value) =>
      state = state.copyWith(productCategoryFilter: value);
  void setShowSellingPrice(bool value) {
    state = state.copyWith(showSellingPrice: value);
    if (!_inventoryAdminMode) {
      StockShowPricePreferences.writeShowSellingPrice(value);
    }
  }

  void setShowLivePrice(bool value) {
    state = state.copyWith(showLivePrice: value);
    if (!_inventoryAdminMode) {
      StockShowPricePreferences.writeShowLivePrice(value);
    }
  }

  Future<void> _ensurePricePreferenceLoaded() async {
    if (_pricePreferenceLoaded || _inventoryAdminMode) return;
    _pricePreferenceLoaded = true;
    final show = await StockShowPricePreferences.readShowSellingPrice();
    final showLive = await StockShowPricePreferences.readShowLivePrice();
    final dismissedAt = await StockShowPricePreferences.readAsusPriceRunDismissedAt();
    state = state.copyWith(
      showSellingPrice: show,
      showLivePrice: showLive,
      asusPriceRunDismissedAt: dismissedAt,
    );
  }

  /// ASUS-only bulk "Update prices" trigger. Progress is tracked server-side
  /// (see `get_asus_bulk_run_status` on the backend), so it survives
  /// navigating away and back, switching apps, or reopening later — call
  /// [syncAsusPriceRunStatus] (e.g. on screen init) to pick up an
  /// already-running or already-finished run without needing to press the
  /// button again.
  Future<void> refreshAsusLivePrices() async {
    state = state.copyWith(asusPriceRunStarting: true, clearError: true);
    try {
      await _ref.read(catalogueRepositoryProvider).refreshAllLivePrices();
      await syncAsusPriceRunStatus();
    } catch (error) {
      state = state.copyWith(error: error.toString());
    } finally {
      state = state.copyWith(asusPriceRunStarting: false);
    }
  }

  /// Fetches real progress from the server and starts/stops polling to
  /// match — call this on screen init as well as after triggering a fresh
  /// run, so returning to the screen mid-run (or after it finished) always
  /// shows the true current state.
  Future<void> syncAsusPriceRunStatus() async {
    AsusPriceRefreshStatus status;
    try {
      status = await _ref.read(catalogueRepositoryProvider).getAsusPriceRefreshStatus();
    } catch (_) {
      return;
    }
    state = state.copyWith(asusPriceRunStatus: status);

    if (status.inProgress > 0) {
      _asusPricePollTimer ??= Timer.periodic(_asusPricePollInterval, (_) {
        unawaited(syncAsusPriceRunStatus());
      });
      return;
    }

    _asusPricePollTimer?.cancel();
    _asusPricePollTimer = null;

    final finishedAt = status.finishedAt;
    if (status.total > 0 && finishedAt != null && _asusPriceRunRefreshedForFinishedAt != finishedAt) {
      _asusPriceRunRefreshedForFinishedAt = finishedAt;
      unawaited(_refreshItemsInBackground(refreshModels: true));
    }
  }

  /// "Retry failed" — re-runs only the models that didn't come back "ok" in
  /// the most recent run. The server remembers which ones failed, so this
  /// doesn't need to pass any IDs — it just starts a fresh, smaller-scoped
  /// bulk run over exactly those models.
  Future<void> retryFailedAsusLivePrices() async {
    state = state.copyWith(asusPriceRunRetrying: true, clearError: true);
    try {
      await _ref.read(catalogueRepositoryProvider).retryFailedLivePrices();
      await syncAsusPriceRunStatus();
    } catch (error) {
      state = state.copyWith(error: error.toString());
    } finally {
      state = state.copyWith(asusPriceRunRetrying: false);
    }
  }

  void dismissAsusPriceRun() {
    final finishedAt = state.asusPriceRunStatus?.finishedAt;
    if (finishedAt == null) return;
    state = state.copyWith(asusPriceRunDismissedAt: finishedAt);
    if (!_inventoryAdminMode) {
      StockShowPricePreferences.writeAsusPriceRunDismissedAt(finishedAt);
    }
  }

  void selectItem(InventoryItem? item) => state = state.copyWith(selectedItem: item, clearSelection: item == null);

  Future<void> openItemBySerial(String serial) async {
    try {
      final result = await _offlineInventory.lookupBySerial(serial);
      final item = result.data;
      if (item != null) {
        state = state.copyWith(
          selectedBrandId: item.brandId,
          selectedModelId: item.productModelId,
          navLevel: InventoryNavLevel.serials,
          selectedItem: item,
          fromCache: result.fromCache,
          isStale: result.isStale,
        );
        return;
      }
      state = state.copyWith(search: serial, searchField: HierarchySearchField.serial);
    } catch (_) {
      state = state.copyWith(search: serial, searchField: HierarchySearchField.serial);
    }
  }

  Future<void> updateProductModel(String modelId, Map<String, dynamic> data) async {
    state = state.copyWith(actionInProgress: true, clearError: true);
    try {
      final updated = await _ref.read(catalogueRepositoryProvider).updateProductModel(modelId, data);
      final models = state.models.map((model) => model.id == modelId ? updated : model).toList();
      state = state.copyWith(models: models, actionInProgress: false);
      unawaited(_refreshItemsInBackground(refreshModels: true));
    } catch (error) {
      state = state.copyWith(actionInProgress: false, error: error.toString());
    }
  }

  Future<void> createProductModel(Map<String, dynamic> data) async {
    state = state.copyWith(actionInProgress: true, clearError: true);
    try {
      final created = await _ref.read(catalogueRepositoryProvider).createProductModel(data);
      state = state.copyWith(
        models: [...state.models, created],
        actionInProgress: false,
      );
      unawaited(_refreshItemsInBackground(refreshModels: true));
    } catch (error) {
      state = state.copyWith(actionInProgress: false, error: error.toString());
    }
  }

  Future<void> deleteProductModel(String modelId) async {
    state = state.copyWith(actionInProgress: true, clearError: true);
    try {
      await _ref.read(catalogueRepositoryProvider).deleteProductModel(modelId);
      if (state.selectedModelId == modelId && state.navLevel == InventoryNavLevel.serials) {
        goBack();
      }
      state = state.copyWith(
        models: state.models.where((model) => model.id != modelId).toList(),
        actionInProgress: false,
      );
      unawaited(_refreshItemsInBackground(refreshModels: true));
    } catch (error) {
      state = state.copyWith(actionInProgress: false, error: error.toString());
    }
  }

  Future<void> updateSellingPrice(String modelId, double? price) async {
    state = state.copyWith(actionInProgress: true, clearError: true);
    try {
      final updated = await _ref.read(catalogueRepositoryProvider).updateSellingPrice(modelId, price);
      final models = state.models
          .map<ProductModel>((model) => model.id == modelId ? updated : model)
          .toList();
      state = state.copyWith(models: models, actionInProgress: false);
    } catch (error) {
      state = state.copyWith(actionInProgress: false, error: error.toString());
    }
  }

  Future<void> transferItem(String itemId, int locationId) async {
    final matches = state.items.where((entry) => entry.id == itemId);
    if (matches.isEmpty) return;
    final item = matches.first;
    state = state.copyWith(selectedItem: item, actionInProgress: true, clearError: true);
    try {
      if (!_isOnline) {
        final pending = _ref.read(pendingOperationFactoryProvider).transferLocation(
              itemId: item.id,
              locationId: locationId,
              entityUpdatedAt: item.updatedAt,
            );
        await _ref.read(backgroundSyncCoordinatorProvider.notifier).enqueuePending(pending);
        state = state.copyWith(actionInProgress: false, isStale: true);
        return;
      }
      final updated = await _inventory.transferLocation(item.id, locationId);
      _applyItemLocally(updated);
      unawaited(_refreshItemsInBackground());
    } catch (error) {
      state = state.copyWith(actionInProgress: false, error: error.toString());
    }
  }

  Future<void> transferSelected(int locationId) async {
    final item = state.selectedItem;
    if (item == null) return;
    state = state.copyWith(actionInProgress: true, clearError: true);
    try {
      if (!_isOnline) {
        final pending = _ref.read(pendingOperationFactoryProvider).transferLocation(
              itemId: item.id,
              locationId: locationId,
              entityUpdatedAt: item.updatedAt,
            );
        await _ref.read(backgroundSyncCoordinatorProvider.notifier).enqueuePending(pending);
        state = state.copyWith(actionInProgress: false, isStale: true);
        return;
      }
      final updated = await _inventory.transferLocation(item.id, locationId);
      _applyItemLocally(updated);
      unawaited(_refreshItemsInBackground());
    } catch (error) {
      state = state.copyWith(actionInProgress: false, error: error.toString());
    }
  }

  Future<void> markSelectedSold(MarkSoldRequest request) async {
    final item = state.selectedItem;
    if (item == null) return;
    await markItemSold(item.id, request);
  }

  Future<void> markItemSold(String itemId, MarkSoldRequest request) async {
    final item = state.items.where((entry) => entry.id == itemId).firstOrNull;
    if (item == null) return;
    state = state.copyWith(actionInProgress: true, clearError: true);
    try {
      if (!_isOnline) {
        final pending = _ref.read(pendingOperationFactoryProvider).markSold(
              itemId: item.id,
              entityUpdatedAt: item.updatedAt,
              request: request.toJson(),
            );
        await _ref.read(backgroundSyncCoordinatorProvider.notifier).enqueuePending(pending);
        state = state.copyWith(actionInProgress: false, isStale: true);
        return;
      }
      final updated = await _inventory.markSold(item.id, request);
      _applyItemLocally(updated);
      unawaited(_refreshItemsInBackground());
    } catch (error) {
      state = state.copyWith(actionInProgress: false, error: error.toString());
    }
  }

  Future<bool> checkSerialDuplicate(String serial) => _inventory.serialExists(serial);

  int availableUnitsForModel(String productModelId) {
    return state.items
        .where((item) =>
            item.productModelId == productModelId &&
            !item.isArchived &&
            item.status != InventoryStatus.sold)
        .length;
  }

  /// Returns true when model and all serials were saved successfully.
  Future<bool> addLaptopWizard(AddLaptopWizardRequest request) async {
    state = state.copyWith(actionInProgress: true, clearError: true);
    try {
      var modelId = request.productModelId;
      if (request.mode == 'new') {
        final payload = request.newProductModel;
        if (payload == null) {
          throw StateError('New product model details are required.');
        }
        final created =
            await _ref.read(catalogueRepositoryProvider).createOrFindProductModel(payload);
        modelId = created.id;
      }
      if (modelId == null || modelId.isEmpty) {
        throw StateError('Product model is required.');
      }

      for (final unit in request.units) {
        final itemRequest = CreateInventoryItemRequest(
          serialNumber: unit.serialNumber.trim(),
          productModelId: modelId,
          color: unit.color.trim().isEmpty
              ? 'Not specified'
              : (unit.color.trim().length <= kInventoryColorMaxLength
                  ? unit.color.trim()
                  : unit.color.trim().substring(0, kInventoryColorMaxLength).trimRight()),
          currentLocationId: unit.currentLocationId,
          purchasePrice: unit.purchasePrice,
        );
        if (!_isOnline) {
          final pending =
              _ref.read(pendingOperationFactoryProvider).createInventory(request: itemRequest.toJson());
          await _ref.read(backgroundSyncCoordinatorProvider.notifier).enqueuePending(pending);
        } else {
          await _inventory.createItem(itemRequest);
        }
      }
      if (_isOnline) {
        state = state.copyWith(actionInProgress: false);
        unawaited(_refreshItemsInBackground(refreshModels: true));
      } else {
        state = state.copyWith(actionInProgress: false, isStale: true);
      }
      return true;
    } catch (error) {
      state = state.copyWith(actionInProgress: false, error: formatApiError(error));
      return false;
    }
  }

  Future<void> createItems(List<CreateInventoryItemRequest> requests) async {
    state = state.copyWith(actionInProgress: true, clearError: true);
    try {
      final created = <InventoryItem>[];
      for (final request in requests) {
        if (!_isOnline) {
          final pending = _ref.read(pendingOperationFactoryProvider).createInventory(request: request.toJson());
          await _ref.read(backgroundSyncCoordinatorProvider.notifier).enqueuePending(pending);
        } else {
          created.add(await _inventory.createItem(request));
        }
      }
      if (_isOnline && created.isNotEmpty) {
        final items = [...state.items, ...created];
        state = state.copyWith(
          items: items,
          brandSummaries: buildBrandSummaries(
            state.brands,
            state.distribution?.byBrand ?? const [],
            items,
          ),
          actionInProgress: false,
        );
        unawaited(_refreshItemsInBackground());
      } else {
        state = state.copyWith(actionInProgress: false, isStale: !_isOnline);
      }
    } catch (error) {
      state = state.copyWith(actionInProgress: false, error: error.toString());
    }
  }

  Future<void> updateSelectedItem(Map<String, dynamic> data) async {
    final item = state.selectedItem;
    if (item == null) return;
    state = state.copyWith(actionInProgress: true, clearError: true);
    try {
      final updated = await _inventory.updateItem(item.id, data);
      _applyItemLocally(updated);
      unawaited(_refreshItemsInBackground());
    } catch (error) {
      state = state.copyWith(actionInProgress: false, error: error.toString());
    }
  }

  Future<void> archiveSelected() async {
    final item = state.selectedItem;
    if (item == null) return;
    state = state.copyWith(actionInProgress: true, clearError: true);
    try {
      await _inventory.archiveItem(item.id);
      final remaining = state.items.where((entry) => entry.id != item.id).toList();
      state = state.copyWith(
        items: remaining,
        clearSelection: true,
        brandSummaries: buildBrandSummaries(
          state.brands,
          state.distribution?.byBrand ?? const [],
          remaining,
        ),
        actionInProgress: false,
      );
      unawaited(_refreshItemsInBackground());
    } catch (error) {
      state = state.copyWith(actionInProgress: false, error: error.toString());
    }
  }

  Future<void> deleteInventoryItem(String itemId) async {
    state = state.copyWith(actionInProgress: true, clearError: true);
    try {
      await _inventory.deleteItem(itemId);
      final remaining = state.items.where((entry) => entry.id != itemId).toList();
      state = state.copyWith(
        items: remaining,
        clearSelection: true,
        brandSummaries: buildBrandSummaries(
          state.brands,
          state.distribution?.byBrand ?? const [],
          remaining,
        ),
        actionInProgress: false,
      );
      unawaited(_refreshItemsInBackground(refreshModels: true));
    } catch (error) {
      state = state.copyWith(actionInProgress: false, error: formatApiError(error));
    }
  }

  Future<void> restoreSelected() async {
    final item = state.selectedItem;
    if (item == null) return;
    state = state.copyWith(actionInProgress: true, clearError: true);
    try {
      final updated = await _inventory.restoreItem(item.id);
      _applyItemLocally(updated);
      unawaited(_refreshItemsInBackground());
    } catch (error) {
      state = state.copyWith(actionInProgress: false, error: error.toString());
    }
  }

  Future<void> _refreshItems({bool refreshModels = false}) async {
    final result = await _offlineInventory.loadWorkspace(forceRefresh: true);
    final workspace = result.data;
    state = state.copyWith(
      models: refreshModels ? workspace.models : state.models,
      distribution: workspace.distribution,
      items: workspace.items,
      brandSummaries: buildBrandSummaries(state.brands, workspace.distribution.byBrand, workspace.items),
      fromCache: result.fromCache,
      isStale: result.isStale,
    );
  }

  void _applyItemLocally(InventoryItem updated) {
    final items = [
      for (final entry in state.items)
        if (entry.id == updated.id) updated else entry,
    ];
    final distribution = state.distribution;
    state = state.copyWith(
      items: items,
      selectedItem: state.selectedItem?.id == updated.id ? updated : state.selectedItem,
      brandSummaries: buildBrandSummaries(
        state.brands,
        distribution?.byBrand ?? const [],
        items,
      ),
      actionInProgress: false,
    );
  }

  Future<void> _refreshItemsInBackground({bool refreshModels = false}) async {
    try {
      await _refreshItems(refreshModels: refreshModels);
    } catch (_) {
      // Keep the optimistic UI; pull-to-refresh recovers if the quiet sync fails.
    }
  }
}

final dashboardDataProvider = FutureProvider.autoDispose<OfflineLoadResult<DashboardCacheBundle>>((ref) async {
  return ref.watch(offlineDashboardServiceProvider).loadDashboard();
});
