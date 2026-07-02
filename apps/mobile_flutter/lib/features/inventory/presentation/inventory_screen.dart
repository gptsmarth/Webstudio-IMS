import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/rbac/mobile_navigation.dart';
import '../../../core/rbac/role_permissions.dart';
import '../../../core/theme/app_breakpoints.dart';
import '../../../core/theme/app_spacing.dart';
import '../../auth/presentation/auth_controller.dart';
import '../../../shared/widgets/brand_logo_image.dart';
import '../../../shared/widgets/placeholders.dart';
import '../../shell/presentation/shell_chrome_controller.dart';
import '../../../shared/widgets/workspace_lookup_sheet.dart';
import '../domain/barcode_field_resolver.dart';
import '../domain/inventory_hierarchy.dart';
import '../domain/inventory_permissions.dart' as inv_perms;
import '../domain/inventory_models.dart';
import '../domain/stock_model_card_utils.dart';
import 'inventory_controller.dart';
import '../../../core/device/barcode_scan_launcher.dart';
import 'widgets/add_laptop_wizard.dart';
import 'widgets/inventory_detail_sheet.dart';
import 'widgets/inventory_filters_sheet.dart';
import 'widgets/stock_brand_grid.dart';
import 'widgets/stock_brand_summary_panel.dart';
import 'widgets/stock_model_card.dart';
import 'widgets/stock_model_detail_view.dart';
import 'widgets/product_model_form_sheet.dart';

class InventoryScreen extends ConsumerStatefulWidget {
  const InventoryScreen({super.key, this.stockBrowseMode = false});

  /// Customer-facing stock browse (desktop Stock page). Admins get this on the Stock tab.
  final bool stockBrowseMode;

  @override
  ConsumerState<InventoryScreen> createState() => _InventoryScreenState();
}

class _InventoryScreenState extends ConsumerState<InventoryScreen> {
  InventoryWorkspaceProvider get _provider =>
      widget.stockBrowseMode ? stockWorkspaceProvider : inventoryAdminWorkspaceProvider;

  bool _modelSearchExpanded = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(_provider.notifier).load();
      _syncShellChrome(ref.read(_provider));
    });
  }

  void _toggleModelSearch() {
    setState(() {
      _modelSearchExpanded = !_modelSearchExpanded;
      if (!_modelSearchExpanded) {
        ref.read(_provider.notifier).setSearch('');
      }
    });
    _syncShellChrome(ref.read(_provider));
  }

  void _closeModelSearch() {
    if (!_modelSearchExpanded) return;
    setState(() => _modelSearchExpanded = false);
    ref.read(_provider.notifier).setSearch('');
    _syncShellChrome(ref.read(_provider));
  }

  @override
  void dispose() {
    ref.read(shellChromeProvider.notifier).clear();
    super.dispose();
  }

  void _syncShellChrome(InventoryWorkspaceState workspace) {
    final chrome = ref.read(shellChromeProvider.notifier);
    if (workspace.navLevel == InventoryNavLevel.brands) {
      chrome.clear();
      return;
    }

    final showModelSearch = workspace.navLevel == InventoryNavLevel.models;

    chrome.set(
      title: _shellTitle(workspace),
      onBack: () {
        _closeModelSearch();
        ref.read(_provider.notifier).goBack();
      },
      hideGlobalSearch: showModelSearch,
    );
  }

  String _shellTitle(InventoryWorkspaceState workspace) {
    return switch (workspace.navLevel) {
      InventoryNavLevel.models => workspace.selectedBrand?.name ?? 'Models',
      InventoryNavLevel.serials => () {
          final model = workspace.selectedModel;
          if (model == null) return 'Model';
          final brand = workspace.selectedBrand?.name ?? '';
          final title = displayModelTitle(brand, model.modelName);
          return title.isNotEmpty ? title : model.modelNumber;
        }(),
      InventoryNavLevel.brands => widget.stockBrowseMode ? 'Stock' : 'Inventory',
    };
  }

  Future<void> _scanBarcode() async {
    final scan = await openBarcodeScanner(context, ref);
    if (scan == null || !mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('${scan.targetField.label}: ${scan.rawValue}')),
    );

    final controller = ref.read(_provider.notifier);
    final field = switch (scan.targetField) {
      BarcodeFieldTarget.serialNumber => HierarchySearchField.serial,
      BarcodeFieldTarget.modelNumber => HierarchySearchField.modelNumber,
      BarcodeFieldTarget.partNumber => HierarchySearchField.modelNumber,
    };
    controller.setSearchField(field);
    controller.setSearch(scan.rawValue);

    if (scan.targetField == BarcodeFieldTarget.serialNumber) {
      await controller.openItemBySerial(scan.rawValue);
      final item = ref.read(_provider).selectedItem;
      if (item != null && mounted) _openDetail(item);
    }
  }

  void _openDetail(InventoryItem item) {
    ref.read(_provider.notifier).selectItem(item);
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (_) => InventoryDetailSheet(workspaceProvider: _provider),
    ).whenComplete(() => ref.read(_provider.notifier).selectItem(null));
  }

  Future<void> _openLookup() async {
    final result = await showWorkspaceLookupSheet(context, ref);
    if (result?.inventoryItem != null && mounted) {
      _openDetail(result!.inventoryItem!);
    }
  }

  @override
  Widget build(BuildContext context) {
    final workspace = ref.watch(_provider);
    ref.listen<InventoryWorkspaceState>(_provider, (previous, next) {
      if (previous?.navLevel != next.navLevel && next.navLevel != InventoryNavLevel.models) {
        _closeModelSearch();
      }
      _syncShellChrome(next);
    });
    final controller = ref.read(_provider.notifier);
    final permissions = effectivePermissions(ref.watch(authControllerProvider).user);
    final canCreate = inv_perms.canCreateInventory(permissions);
    final canCreateModel = inv_perms.canCreateProductModels(permissions);
    final stockOnly = isStockOnlyUser(permissions) || widget.stockBrowseMode;
    final showPrices = stockOnly ? workspace.showSellingPrice : true;
    final atModelsLevel = workspace.navLevel == InventoryNavLevel.models;

    return Scaffold(
      body: Column(
        children: [
          if (workspace.loading) const LinearProgressIndicator(minHeight: 2),
          if (workspace.error != null)
            Material(
              color: Theme.of(context).colorScheme.errorContainer,
              child: ListTile(
                title: Text(workspace.error!),
                trailing: TextButton(onPressed: controller.load, child: const Text('Retry')),
              ),
            ),
          Expanded(
            child: _InventoryBody(
              workspace: workspace,
              workspaceProvider: _provider,
              stockOnly: stockOnly,
              showPrices: showPrices,
              showAdminPrices: !stockOnly,
              modelSearchExpanded: _modelSearchExpanded,
              onToggleModelSearch: atModelsLevel ? _toggleModelSearch : null,
              onSearchChanged: controller.setSearch,
              onCloseModelSearch: _closeModelSearch,
              onScan: _scanBarcode,
              onLookup: stockOnly ? null : _openLookup,
              onFilter: stockOnly
                  ? null
                  : () async {
                      final filters = await showInventoryFiltersSheet(
                        context,
                        initial: workspace.filters,
                        locations: workspace.locations,
                      );
                      if (filters != null) controller.setFilters(filters);
                    },
              onSearchField: () async {
                final field = await showSearchFieldSheet(context, workspace.searchField);
                if (field != null) controller.setSearchField(field);
              },
              onSelectItem: _openDetail,
              onTogglePrices: controller.setShowSellingPrice,
              onToggleZeroStock: controller.setShowZeroStock,
            ),
          ),
        ],
      ),
      floatingActionButton: !widget.stockBrowseMode && workspace.navLevel == InventoryNavLevel.models
          ? () {
              final brand = workspace.selectedBrand;
              if (canCreate && brand != null) {
                return FloatingActionButton.extended(
                  onPressed: () {
                    showAddLaptopWizard(
                      context,
                      ref,
                      brandId: brand.id,
                      brandName: brand.name,
                      workspaceProvider: _provider,
                    );
                  },
                  icon: const Icon(Icons.add),
                  label: const Text('Add laptop'),
                );
              }
              if (canCreateModel) {
                return FloatingActionButton.extended(
                  onPressed: () {
                    showProductModelFormSheet(
                      context,
                      ref,
                      workspaceProvider: _provider,
                      defaultBrandId: workspace.selectedBrandId,
                    );
                  },
                  icon: const Icon(Icons.add),
                  label: const Text('Add model'),
                );
              }
              return null;
            }()
          : null,
    );
  }
}

class _InventoryToolbar extends StatefulWidget {
  const _InventoryToolbar({
    required this.expanded,
    required this.workspace,
    required this.stockOnly,
    required this.onSearchChanged,
    required this.onClose,
    required this.onScan,
    required this.onLookup,
    required this.onFilter,
    required this.onSearchField,
    required this.showPrices,
    this.onTogglePrices,
  });

  final bool expanded;
  final InventoryWorkspaceState workspace;
  final bool stockOnly;
  final ValueChanged<String> onSearchChanged;
  final VoidCallback onClose;
  final VoidCallback onScan;
  final VoidCallback? onLookup;
  final VoidCallback? onFilter;
  final VoidCallback onSearchField;
  final bool showPrices;
  final VoidCallback? onTogglePrices;

  @override
  State<_InventoryToolbar> createState() => _InventoryToolbarState();
}

class _InventoryToolbarState extends State<_InventoryToolbar> {
  final _searchController = TextEditingController();

  @override
  void didUpdateWidget(covariant _InventoryToolbar oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.workspace.navLevel != widget.workspace.navLevel) {
      _searchController.clear();
    }
    if (!widget.expanded && oldWidget.expanded) {
      _searchController.clear();
    }
    if (oldWidget.workspace.search != widget.workspace.search && widget.workspace.search.isEmpty) {
      _searchController.clear();
    }
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  bool get _showModelSearch => widget.workspace.navLevel == InventoryNavLevel.models;

  @override
  Widget build(BuildContext context) {
    if (!_showModelSearch || !widget.expanded) {
      return const SizedBox.shrink();
    }

    final theme = Theme.of(context);
    return Material(
      color: theme.colorScheme.surface,
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(AppSpacing.md, AppSpacing.sm, AppSpacing.md, AppSpacing.sm),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.35),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: theme.dividerColor.withValues(alpha: 0.5)),
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _searchController,
                    autofocus: true,
                    decoration: InputDecoration(
                      hintText: hierarchySearchPlaceholder(widget.workspace.searchField),
                      prefixIcon: const Icon(Icons.search, size: 20),
                      border: InputBorder.none,
                      isDense: true,
                      contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 10),
                    ),
                    onChanged: widget.onSearchChanged,
                  ),
                ),
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      IconButton(tooltip: 'Search field', onPressed: widget.onSearchField, icon: const Icon(Icons.tune, size: 20)),
                      if (widget.onLookup != null)
                        IconButton(tooltip: 'Lookup', onPressed: widget.onLookup, icon: const Icon(Icons.manage_search, size: 20)),
                      if (widget.onFilter != null)
                        IconButton(tooltip: 'Filters', onPressed: widget.onFilter, icon: const Icon(Icons.filter_list, size: 20)),
                      if (widget.onTogglePrices != null)
                        IconButton(
                          tooltip: widget.showPrices ? 'Hide prices' : 'Show prices',
                          onPressed: widget.onTogglePrices,
                          icon: Icon(widget.showPrices ? Icons.sell : Icons.sell_outlined, size: 20),
                        ),
                      IconButton(tooltip: 'Scan barcode', onPressed: widget.onScan, icon: const Icon(Icons.qr_code_scanner, size: 20)),
                      IconButton(
                        tooltip: 'Close search',
                        onPressed: widget.onClose,
                        icon: const Icon(Icons.close, size: 20),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _ModelsPriceToggle extends StatelessWidget {
  const _ModelsPriceToggle({required this.showPrices, required this.onChanged});

  final bool showPrices;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Theme.of(context).colorScheme.surfaceContainerLowest,
      child: CheckboxListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
        dense: true,
        value: showPrices,
        onChanged: (value) {
          if (value != null) onChanged(value);
        },
        title: const Text('Show selling prices on cards'),
        controlAffinity: ListTileControlAffinity.leading,
      ),
    );
  }
}

class _ZeroStockToggle extends StatelessWidget {
  const _ZeroStockToggle({required this.showZeroStock, required this.onChanged});

  final bool showZeroStock;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Theme.of(context).colorScheme.surfaceContainerLowest,
      child: CheckboxListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
        dense: true,
        value: showZeroStock,
        onChanged: (value) {
          if (value != null) onChanged(value);
        },
        title: const Text('Show zero-stock models'),
        controlAffinity: ListTileControlAffinity.leading,
      ),
    );
  }
}

String _modelsEmptyMessage(InventoryWorkspaceState workspace, bool stockOnly) {
  if (workspace.search.trim().isNotEmpty) {
    return 'Try a different search term or clear filters.';
  }
  if (stockOnly) {
    return 'Only models with available units appear in Stock. Zero-stock models are managed under Inventory.';
  }
  if (!workspace.showZeroStock) {
    return 'Turn on "Show zero-stock models" to see the full catalogue for this brand.';
  }
  return 'Add models in Catalogue or adjust your filters.';
}

class _InventoryBody extends ConsumerWidget {
  const _InventoryBody({
    required this.workspace,
    required this.workspaceProvider,
    required this.stockOnly,
    required this.showPrices,
    required this.showAdminPrices,
    required this.modelSearchExpanded,
    required this.onToggleModelSearch,
    required this.onSearchChanged,
    required this.onCloseModelSearch,
    required this.onScan,
    required this.onLookup,
    required this.onFilter,
    required this.onSearchField,
    required this.onSelectItem,
    required this.onTogglePrices,
    required this.onToggleZeroStock,
  });

  final InventoryWorkspaceState workspace;
  final InventoryWorkspaceProvider workspaceProvider;
  final bool stockOnly;
  final bool showPrices;
  final bool showAdminPrices;
  final bool modelSearchExpanded;
  final VoidCallback? onToggleModelSearch;
  final ValueChanged<String> onSearchChanged;
  final VoidCallback onCloseModelSearch;
  final VoidCallback onScan;
  final VoidCallback? onLookup;
  final VoidCallback? onFilter;
  final VoidCallback onSearchField;
  final void Function(InventoryItem item) onSelectItem;
  final ValueChanged<bool> onTogglePrices;
  final ValueChanged<bool> onToggleZeroStock;

  static const _scrollBottomPadding = 96.0;

  List<Widget> _modelsHeaderWidgets(BuildContext context) {
    return [
      if (stockOnly && workspace.selectedBrandSummary != null)
        StockBrandSummaryPanel(
          summary: workspace.selectedBrandSummary!,
          brandName: workspace.selectedBrand?.name,
        ),
      if (workspace.selectedBrand != null)
        Padding(
          padding: const EdgeInsets.fromLTRB(AppSpacing.md, 0, AppSpacing.md, AppSpacing.sm),
          child: Row(
            children: [
              Expanded(
                child: BrandLogoImage(
                  brandName: workspace.selectedBrand!.name,
                  logoFilename: workspace.selectedBrand!.logoFilename,
                  height: 36,
                  maxWidth: 120,
                ),
              ),
              if (onToggleModelSearch != null)
                IconButton(
                  tooltip: modelSearchExpanded ? 'Close search' : 'Search models',
                  onPressed: onToggleModelSearch,
                  icon: Icon(modelSearchExpanded ? Icons.close : Icons.search),
                  style: modelSearchExpanded
                      ? IconButton.styleFrom(
                          backgroundColor: Theme.of(context).colorScheme.secondaryContainer,
                        )
                      : null,
                ),
            ],
          ),
        ),
      if (stockOnly)
        _ModelsPriceToggle(
          showPrices: showPrices,
          onChanged: onTogglePrices,
        ),
      if (!stockOnly)
        _ZeroStockToggle(
          showZeroStock: workspace.showZeroStock,
          onChanged: onToggleZeroStock,
        ),
      if (modelSearchExpanded)
        _InventoryToolbar(
          expanded: true,
          workspace: workspace,
          stockOnly: stockOnly,
          onSearchChanged: onSearchChanged,
          onClose: onCloseModelSearch,
          onScan: onScan,
          onLookup: onLookup,
          onFilter: onFilter,
          onSearchField: onSearchField,
          onTogglePrices: null,
          showPrices: showPrices,
        ),
    ];
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (workspace.loading && workspace.brandSummaries.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    return switch (workspace.navLevel) {
      InventoryNavLevel.brands => RefreshIndicator(
          onRefresh: () => ref.read(workspaceProvider.notifier).load(),
          child: stockOnly
              ? StockBrandGrid(
                  brands: workspace.visibleBrands,
                  onSelect: (brand) => ref.read(workspaceProvider.notifier).selectBrand(brand.brandId),
                )
              : ListView(
                  padding: const EdgeInsets.all(AppSpacing.md),
                  children: [
                    for (final brand in workspace.visibleBrands)
                      InventoryBrandCard(
                        brand: brand,
                        showSoldUnits: false,
                        onTap: () => ref.read(workspaceProvider.notifier).selectBrand(brand.brandId),
                      ),
                  ],
                ),
        ),
      InventoryNavLevel.models => RefreshIndicator(
          onRefresh: () => ref.read(workspaceProvider.notifier).load(),
          child: workspace.visibleModels.isEmpty
              ? ListView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.only(bottom: _scrollBottomPadding),
                  children: [
                    ..._modelsHeaderWidgets(context),
                    SizedBox(height: stockOnly ? 40 : 80),
                    EmptyStateView(
                      icon: stockOnly ? Icons.laptop_outlined : Icons.inventory_2_outlined,
                      title: stockOnly ? 'No in-stock models' : 'No models for this brand',
                      message: _modelsEmptyMessage(workspace, stockOnly),
                    ),
                  ],
                )
              : LayoutBuilder(
                  builder: (context, constraints) {
                    final columns = AppBreakpoints.gridColumns(context, phone: 2, tablet: 3, desktop: 4);
                    final horizontalPad = AppSpacing.lg * 2;
                    final gap = 14.0 * (columns - 1);
                    final cardWidth = (constraints.maxWidth - horizontalPad - gap) / columns;
                    return ListView(
                      physics: const AlwaysScrollableScrollPhysics(),
                      padding: const EdgeInsets.only(bottom: _scrollBottomPadding),
                      children: [
                        ..._modelsHeaderWidgets(context),
                        Padding(
                          padding: const EdgeInsets.all(AppSpacing.md),
                          child: Wrap(
                            spacing: 14,
                            runSpacing: 14,
                            children: [
                              for (final row in workspace.visibleModels)
                                SizedBox(
                                  width: cardWidth,
                                  child: StockModelCard(
                                    row: row,
                                    brandName: workspace.selectedBrand?.name,
                                    showPrice: showPrices,
                                    showAdminPrices: showAdminPrices,
                                    onTap: () => ref.read(workspaceProvider.notifier).selectModel(row.model.id),
                                  ),
                                ),
                            ],
                          ),
                        ),
                      ],
                    );
                  },
                ),
        ),
      InventoryNavLevel.serials => () {
          final model = workspace.selectedModel;
          if (model == null) {
            return const Center(child: Text('Model not found'));
          }
          return StockModelDetailView(
            model: model,
            brandName: workspace.selectedBrand?.name ?? '',
            brandLogoFilename: workspace.selectedBrand?.logoFilename,
            units: showAdminPrices
                ? workspace.serialUnitsForSelectedModel
                : workspace.availableUnitsForSelectedModel,
            locations: workspace.locations,
            actionInProgress: workspace.actionInProgress,
            brands: workspace.brands,
            workspaceProvider: workspaceProvider,
            inventoryAdminMode: showAdminPrices,
            onSelectUnit: onSelectItem,
          );
        }(),
    };
  }
}
