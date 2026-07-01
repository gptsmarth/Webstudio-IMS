import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../inventory/data/inventory_repository.dart';
import '../../inventory/domain/inventory_models.dart';
import '../data/sales_repository.dart';
import '../domain/sales_models.dart';

class SalespersonOption {
  const SalespersonOption({required this.id, required this.displayName});

  final int id;
  final String displayName;
}

class SalesWorkspaceState {
  const SalesWorkspaceState({
    this.loading = false,
    this.error,
    this.items = const [],
    this.brands = const [],
    this.locations = const [],
    this.salespeople = const [],
    this.search = '',
    this.filters = const SalesListFilters(),
    this.page = 1,
    this.pageSize = 50,
    this.totalItems = 0,
    this.totalPages = 1,
    this.sortField = SalesSortField.soldAt,
    this.sortDirection = 'desc',
    this.selectedId,
    this.selectedDetail,
    this.detailLoading = false,
  });

  final bool loading;
  final String? error;
  final List<SaleListItem> items;
  final List<Brand> brands;
  final List<Location> locations;
  final List<SalespersonOption> salespeople;
  final String search;
  final SalesListFilters filters;
  final int page;
  final int pageSize;
  final int totalItems;
  final int totalPages;
  final SalesSortField sortField;
  final String sortDirection;
  final int? selectedId;
  final SaleDetail? selectedDetail;
  final bool detailLoading;

  SaleListItem? get selectedItem {
    if (selectedId == null) return null;
    for (final item in items) {
      if (item.id == selectedId) return item;
    }
    return null;
  }

  SalesWorkspaceState copyWith({
    bool? loading,
    String? error,
    List<SaleListItem>? items,
    List<Brand>? brands,
    List<Location>? locations,
    List<SalespersonOption>? salespeople,
    String? search,
    SalesListFilters? filters,
    int? page,
    int? pageSize,
    int? totalItems,
    int? totalPages,
    SalesSortField? sortField,
    String? sortDirection,
    int? selectedId,
    SaleDetail? selectedDetail,
    bool? detailLoading,
    bool clearError = false,
    bool clearSelection = false,
  }) {
    return SalesWorkspaceState(
      loading: loading ?? this.loading,
      error: clearError ? null : error ?? this.error,
      items: items ?? this.items,
      brands: brands ?? this.brands,
      locations: locations ?? this.locations,
      salespeople: salespeople ?? this.salespeople,
      search: search ?? this.search,
      filters: filters ?? this.filters,
      page: page ?? this.page,
      pageSize: pageSize ?? this.pageSize,
      totalItems: totalItems ?? this.totalItems,
      totalPages: totalPages ?? this.totalPages,
      sortField: sortField ?? this.sortField,
      sortDirection: sortDirection ?? this.sortDirection,
      selectedId: clearSelection ? null : selectedId ?? this.selectedId,
      selectedDetail: clearSelection ? null : selectedDetail ?? this.selectedDetail,
      detailLoading: detailLoading ?? this.detailLoading,
    );
  }
}

final salesWorkspaceProvider = StateNotifierProvider<SalesWorkspaceController, SalesWorkspaceState>((ref) {
  return SalesWorkspaceController(ref);
});

class SalesWorkspaceController extends StateNotifier<SalesWorkspaceState> {
  SalesWorkspaceController(this._ref) : super(const SalesWorkspaceState());

  final Ref _ref;

  SalesRepository get _sales => _ref.read(salesRepositoryProvider);
  InventoryRepository get _inventory => _ref.read(inventoryRepositoryProvider);

  Future<void> load() async {
    state = state.copyWith(loading: true, clearError: true);
    try {
      if (state.brands.isEmpty) {
        final brands = await _inventory.listBrands();
        final locations = await _inventory.listLocations();
        state = state.copyWith(brands: brands, locations: locations);
      }
      await _fetchPage();
    } catch (error) {
      state = state.copyWith(loading: false, error: error.toString());
    }
  }

  Future<void> _fetchPage() async {
    final result = await _sales.listSales(
      filters: state.filters,
      search: state.search,
      page: state.page,
      pageSize: state.pageSize,
      sortField: state.sortField,
      sortDirection: state.sortDirection,
    );
    final salespeople = _buildSalespeople(result.items);
    state = state.copyWith(
      loading: false,
      items: result.items,
      totalItems: result.totalItems,
      totalPages: result.totalPages,
      salespeople: salespeople,
    );
  }

  List<SalespersonOption> _buildSalespeople(List<SaleListItem> items) {
    final map = <int, String>{};
    for (final item in items) {
      final id = item.recordedByUserId;
      final name = item.recordedByDisplayName;
      if (id != null && name != null && name.isNotEmpty) {
        map[id] = name;
      }
    }
    return map.entries
        .map((e) => SalespersonOption(id: e.key, displayName: e.value))
        .toList()
      ..sort((a, b) => a.displayName.compareTo(b.displayName));
  }

  void setSearch(String value) {
    state = state.copyWith(search: value, page: 1);
    _debouncedRefresh();
  }

  void setFilters(SalesListFilters filters) {
    state = state.copyWith(filters: filters, page: 1);
    refresh();
  }

  void resetFilters() {
    state = state.copyWith(filters: const SalesListFilters(), page: 1);
    refresh();
  }

  void setPage(int page) {
    state = state.copyWith(page: page);
    refresh();
  }

  void toggleSort(SalesSortField field) {
    if (state.sortField == field) {
      final next = state.sortDirection == 'asc' ? 'desc' : 'asc';
      state = state.copyWith(sortDirection: next, page: 1);
    } else {
      state = state.copyWith(
        sortField: field,
        sortDirection: field == SalesSortField.soldAt ? 'desc' : 'asc',
        page: 1,
      );
    }
    refresh();
  }

  Future<void> refresh() async {
    state = state.copyWith(loading: true, clearError: true);
    try {
      await _fetchPage();
    } catch (error) {
      state = state.copyWith(loading: false, error: error.toString());
    }
  }

  Future<void> selectSale(int? id) async {
    if (id == null) {
      state = state.copyWith(clearSelection: true);
      return;
    }
    state = state.copyWith(selectedId: id, detailLoading: true, clearSelection: false);
    try {
      final detail = await _sales.getSale(id);
      state = state.copyWith(selectedDetail: detail, detailLoading: false);
    } catch (error) {
      state = state.copyWith(detailLoading: false, error: error.toString());
    }
  }

  Future<void> openSaleBySearch(String term) async {
    state = state.copyWith(search: term, page: 1);
    await refresh();
    if (state.items.isNotEmpty) {
      await selectSale(state.items.first.id);
    }
  }

  void _debouncedRefresh() {
    Future<void>.delayed(const Duration(milliseconds: 300), () {
      if (!mounted) return;
      refresh();
    });
  }
}
