import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_spacing.dart';
import '../../../shared/widgets/placeholders.dart';
import '../../../shared/widgets/scrollable_bottom_sheet.dart';
import '../../../shared/widgets/workspace_lookup_sheet.dart';
import '../../auth/presentation/auth_controller.dart';
import '../domain/catalogue_models.dart';
import 'widgets/catalogue_form_sheets.dart';
import 'catalogue_controller.dart';

class CatalogueScreen extends ConsumerStatefulWidget {
  const CatalogueScreen({super.key});

  @override
  ConsumerState<CatalogueScreen> createState() => _CatalogueScreenState();
}

class _CatalogueScreenState extends ConsumerState<CatalogueScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(catalogueWorkspaceProvider.notifier).load();
    });
  }

  Future<void> _addBrand() async {
    final name = await _promptText(context, title: 'Add brand', label: 'Brand name');
    if (!mounted) return;
    if (name != null && name.trim().isNotEmpty) {
      await ref.read(catalogueWorkspaceProvider.notifier).createBrand(name.trim());
    }
  }

  Future<void> _addLocation() async {
    final name = await _promptText(context, title: 'Add location', label: 'Location name');
    if (!mounted) return;
    if (name == null || name.trim().isEmpty) return;
    final type = await showDialog<String>(
      context: context,
      builder: (context) => SimpleDialog(
        title: const Text('Location type'),
        children: [
          SimpleDialogOption(onPressed: () => Navigator.pop(context, 'retail_floor'), child: const Text('Retail floor')),
          SimpleDialogOption(onPressed: () => Navigator.pop(context, 'warehouse'), child: const Text('Warehouse')),
          SimpleDialogOption(onPressed: () => Navigator.pop(context, 'other'), child: const Text('Other')),
        ],
      ),
    );
    if (!mounted) return;
    if (type != null) {
      await ref.read(catalogueWorkspaceProvider.notifier).createLocation(name.trim(), type);
    }
  }

  @override
  Widget build(BuildContext context) {
    final workspace = ref.watch(catalogueWorkspaceProvider);
    final controller = ref.read(catalogueWorkspaceProvider.notifier);
    final permissions = ref.watch(authControllerProvider).user?.permissions ?? const <String>[];
    final canWrite = canWriteCatalogue(permissions);

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(AppSpacing.md, AppSpacing.sm, AppSpacing.md, 0),
          child: SegmentedButton<CatalogueTab>(
            segments: const [
              ButtonSegment(value: CatalogueTab.brands, label: Text('Brands')),
              ButtonSegment(value: CatalogueTab.locations, label: Text('Locations')),
            ],
            selected: {workspace.tab},
            onSelectionChanged: (selection) => controller.setTab(selection.first),
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(AppSpacing.md, AppSpacing.sm, AppSpacing.md, AppSpacing.sm),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  decoration: InputDecoration(
                    hintText: workspace.tab == CatalogueTab.brands ? 'Search brands…' : 'Search locations…',
                    prefixIcon: const Icon(Icons.search, size: 20),
                    isDense: true,
                  ),
                  onChanged: controller.setSearch,
                ),
              ),
              IconButton(
                icon: const Icon(Icons.sort),
                tooltip: 'Sort',
                onPressed: () => _showSortMenu(context, workspace, controller),
              ),
              IconButton(
                icon: const Icon(Icons.manage_search),
                tooltip: 'Lookup',
                onPressed: () => showWorkspaceLookupSheet(context, ref),
              ),
              if (canWrite)
                IconButton(
                  icon: const Icon(Icons.add),
                  onPressed: workspace.tab == CatalogueTab.brands ? _addBrand : _addLocation,
                ),
              IconButton(icon: const Icon(Icons.refresh), onPressed: controller.load),
            ],
          ),
        ),
        if (workspace.tab == CatalogueTab.locations)
          CheckboxListTile(
            title: const Text('Include archived'),
            value: workspace.includeArchived,
            onChanged: (v) => controller.setIncludeArchived(v ?? false),
            controlAffinity: ListTileControlAffinity.leading,
            contentPadding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
          ),
        if (workspace.loading) const LinearProgressIndicator(minHeight: 2),
        if (workspace.error != null)
          Material(
            color: Theme.of(context).colorScheme.errorContainer,
            child: ListTile(title: Text(workspace.error!)),
          ),
        Expanded(
          child: RefreshIndicator(
            onRefresh: controller.load,
            child: workspace.tab == CatalogueTab.brands
                ? _BrandsList(workspace: workspace, canWrite: canWrite)
                : _LocationsList(workspace: workspace, canWrite: canWrite),
          ),
        ),
        _CataloguePagination(workspace: workspace, onPage: controller.setPage),
      ],
    );
  }
}

class _BrandsList extends ConsumerWidget {
  const _BrandsList({required this.workspace, required this.canWrite});

  final CatalogueWorkspaceState workspace;
  final bool canWrite;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final items = paginateItems(workspace.visibleBrands, workspace.page, cataloguePageSize);
    if (items.isEmpty) {
      return const EmptyStateView(
        icon: Icons.branding_watermark_outlined,
        title: 'No brands found',
        message: 'Add a brand or adjust your search filters.',
      );
    }

    return ListView.separated(
      itemCount: items.length,
      separatorBuilder: (_, __) => const Divider(height: 1),
      itemBuilder: (context, index) {
        final brand = items[index];
        final stock = workspace.stockByBrandId['${brand.id}'];
        final modelCount = workspace.modelCountsByBrand[brand.id] ?? 0;
        return ListTile(
          title: Text(brand.name),
          subtitle: Text('$modelCount models · ${stock?.available ?? 0} available'),
          onTap: canWrite ? () => showEditBrandSheet(context, ref, brand) : null,
          trailing: canWrite
              ? PopupMenuButton<String>(
                  onSelected: (action) async {
                    final ctrl = ref.read(catalogueWorkspaceProvider.notifier);
                    if (action == 'edit') {
                      await showEditBrandSheet(context, ref, brand);
                    }
                    if (action == 'delete') {
                      final confirmed = await showDialog<bool>(
                        context: context,
                        builder: (context) => AlertDialog(
                          title: Text('Delete ${brand.name}?'),
                          content: const Text(
                            'This permanently removes the brand and all of its product models and serial numbers still in stock. Past sales and audit history are preserved.',
                          ),
                          actions: [
                            TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
                            TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Delete')),
                          ],
                        ),
                      );
                      if (!context.mounted) return;
                      if (confirmed == true) await ctrl.deleteBrand(brand.id);
                    }
                  },
                  itemBuilder: (_) => [
                    const PopupMenuItem(value: 'edit', child: Text('Edit')),
                    const PopupMenuItem(value: 'delete', child: Text('Delete')),
                  ],
                )
              : null,
        );
      },
    );
  }
}

class _LocationsList extends ConsumerWidget {
  const _LocationsList({required this.workspace, required this.canWrite});

  final CatalogueWorkspaceState workspace;
  final bool canWrite;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final items = paginateItems(workspace.visibleLocations, workspace.page, cataloguePageSize);
    if (items.isEmpty) {
      return const EmptyStateView(
        icon: Icons.location_on_outlined,
        title: 'No locations found',
        message: 'Add a location or adjust your search filters.',
      );
    }

    return ListView.separated(
      itemCount: items.length,
      separatorBuilder: (_, __) => const Divider(height: 1),
      itemBuilder: (context, index) {
        final location = items[index];
        final stock = workspace.stockByLocationId['${location.id}'];
        return ListTile(
          title: Text(location.name),
          subtitle: Text(
            '${locationTypeLabel(location.locationType)} · '
            '${stock?.available ?? 0} in stock · ${stock?.total ?? 0} capacity',
          ),
          onTap: canWrite ? () => showEditLocationSheet(context, ref, location, workspace.locations) : null,
          trailing: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Chip(
                label: Text(location.isActive ? 'Active' : 'Archived'),
                visualDensity: VisualDensity.compact,
              ),
              if (canWrite)
                PopupMenuButton<String>(
                  onSelected: (action) async {
                    final ctrl = ref.read(catalogueWorkspaceProvider.notifier);
                    if (action == 'edit') await showEditLocationSheet(context, ref, location, workspace.locations);
                    if (action == 'archive') await ctrl.archiveLocation(location.id);
                    if (action == 'restore') await ctrl.restoreLocation(location.id);
                  },
                  itemBuilder: (_) => [
                    const PopupMenuItem(value: 'edit', child: Text('Edit')),
                    if (location.isActive)
                      const PopupMenuItem(value: 'archive', child: Text('Archive'))
                    else
                      const PopupMenuItem(value: 'restore', child: Text('Restore')),
                  ],
                ),
            ],
          ),
        );
      },
    );
  }
}

class _CataloguePagination extends StatelessWidget {
  const _CataloguePagination({required this.workspace, required this.onPage});

  final CatalogueWorkspaceState workspace;
  final ValueChanged<int> onPage;

  @override
  Widget build(BuildContext context) {
    if (workspace.totalPages <= 1) return const SizedBox.shrink();
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.sm),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            IconButton(
              onPressed: workspace.page > 1 ? () => onPage(workspace.page - 1) : null,
              icon: const Icon(Icons.chevron_left),
            ),
            Text('Page ${workspace.page} of ${workspace.totalPages}'),
            IconButton(
              onPressed: workspace.page < workspace.totalPages ? () => onPage(workspace.page + 1) : null,
              icon: const Icon(Icons.chevron_right),
            ),
          ],
        ),
      ),
    );
  }
}

void _showSortMenu(
  BuildContext context,
  CatalogueWorkspaceState workspace,
  CatalogueWorkspaceController controller,
) {
  showScrollableBottomSheet<void>(
    context: context,
    title: 'Sort by',
    children: workspace.tab == CatalogueTab.brands
        ? [
            ListTile(title: const Text('Name'), onTap: () { controller.toggleBrandSort(BrandSortField.name); Navigator.pop(context); }),
            ListTile(title: const Text('Display order'), onTap: () { controller.toggleBrandSort(BrandSortField.displayOrder); Navigator.pop(context); }),
            ListTile(title: const Text('Models'), onTap: () { controller.toggleBrandSort(BrandSortField.models); Navigator.pop(context); }),
            ListTile(title: const Text('Available stock'), onTap: () { controller.toggleBrandSort(BrandSortField.available); Navigator.pop(context); }),
          ]
        : [
            ListTile(title: const Text('Name'), onTap: () { controller.toggleLocationSort(LocationSortField.name); Navigator.pop(context); }),
            ListTile(title: const Text('Type'), onTap: () { controller.toggleLocationSort(LocationSortField.locationType); Navigator.pop(context); }),
            ListTile(title: const Text('Stock'), onTap: () { controller.toggleLocationSort(LocationSortField.stock); Navigator.pop(context); }),
            ListTile(title: const Text('Capacity'), onTap: () { controller.toggleLocationSort(LocationSortField.capacity); Navigator.pop(context); }),
          ],
  );
}

Future<String?> _promptText(BuildContext context, {required String title, required String label}) {
  final controller = TextEditingController();
  return showDialog<String>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(title),
      content: TextField(controller: controller, decoration: InputDecoration(labelText: label)),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
        ElevatedButton(onPressed: () => Navigator.pop(context, controller.text), child: const Text('Save')),
      ],
    ),
  );
}
