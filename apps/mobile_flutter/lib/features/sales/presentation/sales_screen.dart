import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/device/file_transfer_service.dart';
import '../../../core/rbac/role_permissions.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../shared/widgets/adaptive_master_detail.dart';
import '../../../shared/widgets/scrollable_bottom_sheet.dart';
import '../../../shared/widgets/workspace_lookup_sheet.dart';
import '../../auth/presentation/auth_controller.dart';
import '../../reports/data/report_repository.dart';
import '../../reports/domain/report_models.dart';
import '../data/sales_repository.dart';
import '../domain/sales_models.dart';
import '../domain/sales_permissions.dart';
import 'sales_controller.dart';
import 'widgets/sale_cancel_dialog.dart';
import 'widgets/sales_detail_sheet.dart';
import 'widgets/sales_filters_sheet.dart';

class SalesScreen extends ConsumerStatefulWidget {
  const SalesScreen({super.key});

  @override
  ConsumerState<SalesScreen> createState() => _SalesScreenState();
}

class _SalesScreenState extends ConsumerState<SalesScreen> {
  bool _backfilling = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(salesWorkspaceProvider.notifier).load();
    });
  }

  Future<void> _syncOlderSales() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: DateTime(now.year, now.month - 3, 1),
      firstDate: DateTime(now.year - 5),
      lastDate: now,
      helpText: 'Sync sales from Tally starting',
    );
    if (picked == null || !mounted) return;
    final fromDate = '${picked.year.toString().padLeft(4, '0')}-'
        '${picked.month.toString().padLeft(2, '0')}-'
        '${picked.day.toString().padLeft(2, '0')}';
    final messenger = ScaffoldMessenger.of(context);
    setState(() => _backfilling = true);
    try {
      final result =
          await ref.read(salesRepositoryProvider).backfillSales(fromDate: fromDate);
      if (!mounted) return;
      await ref.read(salesWorkspaceProvider.notifier).refresh();
      messenger.showSnackBar(
        SnackBar(
          content: Text(
            'Checked ${result.checked} sales invoice(s) since ${result.fromDate} — '
            '${result.salesCreated} unit(s) marked sold, ${result.skipped} already synced'
            '${result.failures > 0 ? ', ${result.failures} failed' : ''}.',
          ),
        ),
      );
    } catch (error) {
      messenger.showSnackBar(
        SnackBar(content: Text('Failed to sync older sales: $error')),
      );
    } finally {
      if (mounted) setState(() => _backfilling = false);
    }
  }

  void _openDetail(int saleId) {
    ref.read(salesWorkspaceProvider.notifier).selectSale(saleId);
    final useSplit = MediaQuery.sizeOf(context).width >= 900;
    if (useSplit) return;
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (_) => const SalesDetailSheet(),
    ).whenComplete(() => ref.read(salesWorkspaceProvider.notifier).selectSale(null));
  }

  Future<void> _exportSales(String format) async {
    final workspace = ref.read(salesWorkspaceProvider);
    final filters = workspace.filters;
    final params = ReportQueryParams(
      search: workspace.search,
      dateFrom: filters.dateFrom,
      dateTo: filters.dateTo,
      brandId: filters.brandId,
      locationId: filters.locationId,
      pageSize: 500,
    );
    final messenger = ScaffoldMessenger.of(context);
    try {
      final file = await ref.read(reportRepositoryProvider).exportReport(
            ReportType.sales,
            params,
            format: format,
          );
      if (!mounted) return;
      final transfer = ref.read(fileTransferServiceProvider);
      await showScrollableBottomSheet<void>(
        context: context,
        title: 'Export sales',
        children: [
          ListTile(
            leading: const Icon(Icons.save_alt),
            title: const Text('Download report'),
            onTap: () async {
              Navigator.pop(context);
              await transfer.saveToDocuments(filename: file.filename, bytes: file.bytes);
              if (!context.mounted) return;
              messenger.showSnackBar(SnackBar(content: Text('Saved ${file.filename}')));
            },
          ),
          ListTile(
            leading: const Icon(Icons.ios_share),
            title: const Text('Share report'),
            onTap: () async {
              Navigator.pop(context);
              await transfer.shareFile(
                filename: file.filename,
                bytes: file.bytes,
                mimeType: file.mimeType,
              );
            },
          ),
        ],
      );
    } catch (error) {
      messenger.showSnackBar(SnackBar(content: Text(error.toString())));
    }
  }

  Future<void> _openLookup() async {
    final result = await showWorkspaceLookupSheet(context, ref);
    if (result?.saleId != null && mounted) {
      _openDetail(result!.saleId!);
    }
  }

  Future<void> _confirmDeleteSale(SaleListItem sale) async {
    final reasonInput = await showSaleCancelDialog(context, sale);
    if (reasonInput == null || !mounted) return;

    final messenger = ScaffoldMessenger.of(context);
    final controller = ref.read(salesWorkspaceProvider.notifier);
    try {
      final result = await controller.cancelSale(
        sale.id,
        reason: reasonInput.isEmpty ? null : reasonInput,
      );
      if (!mounted) return;
      messenger.showSnackBar(
        SnackBar(
          content: Text(
            'Invoice ${result.invoiceNumber} deleted — ${result.restoredSerialNumber} back in stock',
          ),
        ),
      );
    } catch (error) {
      messenger.showSnackBar(SnackBar(content: Text(error.toString())));
    }
  }

  @override
  Widget build(BuildContext context) {
    final workspace = ref.watch(salesWorkspaceProvider);
    final controller = ref.read(salesWorkspaceProvider.notifier);
    final permissions = effectivePermissions(ref.watch(authControllerProvider).user);

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(AppSpacing.md, AppSpacing.sm, AppSpacing.md, AppSpacing.sm),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  decoration: const InputDecoration(
                    hintText: 'Search invoice, customer, serial…',
                    prefixIcon: Icon(Icons.search, size: 20),
                    isDense: true,
                  ),
                  onChanged: controller.setSearch,
                ),
              ),
              IconButton(icon: const Icon(Icons.tune), onPressed: () async {
                final filters = await showSalesFiltersSheet(
                  context,
                  initial: workspace.filters,
                  brands: workspace.brands,
                  locations: workspace.locations,
                  salespeople: workspace.salespeople,
                );
                if (filters != null) controller.setFilters(filters);
              }),
              IconButton(icon: const Icon(Icons.manage_search), tooltip: 'Lookup', onPressed: _openLookup),
              if (permissions.contains('tally:run_sync'))
                IconButton(
                  icon: const Icon(Icons.history),
                  tooltip: 'Sync older sales from Tally',
                  onPressed: _backfilling ? null : _syncOlderSales,
                ),
              PopupMenuButton<String>(
                tooltip: 'Export',
                icon: const Icon(Icons.download_outlined),
                onSelected: _exportSales,
                itemBuilder: (context) => const [
                  PopupMenuItem(value: 'xlsx', child: Text('Export Excel')),
                  PopupMenuItem(value: 'pdf', child: Text('Export PDF')),
                ],
              ),
              IconButton(icon: const Icon(Icons.refresh), onPressed: controller.refresh),
            ],
          ),
        ),
        if (workspace.loading || workspace.actionInProgress)
          const LinearProgressIndicator(minHeight: 2),
        if (workspace.error != null)
          Material(
            color: Theme.of(context).colorScheme.errorContainer,
            child: ListTile(
              title: Text(workspace.error!),
              trailing: TextButton(onPressed: controller.load, child: const Text('Retry')),
            ),
          ),
        if (workspace.actionError != null)
          Material(
            color: Theme.of(context).colorScheme.errorContainer,
            child: ListTile(
              title: Text(workspace.actionError!),
              trailing: TextButton(
                onPressed: controller.clearActionError,
                child: const Text('Dismiss'),
              ),
            ),
          ),
        Expanded(
          child: AdaptiveMasterDetail(
            hasSelection: workspace.selectedDetail != null,
            master: workspace.items.isEmpty && !workspace.loading
                ? const Center(child: Text('No sales found'))
                : RefreshIndicator(
                    onRefresh: controller.refresh,
                    child: ListView.separated(
                      itemCount: workspace.items.length,
                      separatorBuilder: (_, __) => const Divider(height: 1),
                      itemBuilder: (context, index) {
                        final sale = workspace.items[index];
                        final selected = workspace.selectedDetail?.id == sale.id;
                        final canDelete = canDeleteSale(permissions, sale.inventoryItemId);
                        return ListTile(
                          selected: selected,
                          title: Text(sale.invoiceNumber),
                          subtitle: Text(
                            '${sale.customerName ?? '—'} · ${sale.serialNumber}\n'
                            '${sale.brandName} ${sale.modelName} · ${sale.locationName}',
                          ),
                          isThreeLine: true,
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                crossAxisAlignment: CrossAxisAlignment.end,
                                children: [
                                  Text(formatSaleAmount(sale.saleAmount)),
                                  Text(
                                    sale.soldAt.split('T').first,
                                    style: Theme.of(context).textTheme.bodySmall,
                                  ),
                                ],
                              ),
                              if (canDelete)
                                PopupMenuButton<String>(
                                  tooltip: 'Actions',
                                  onSelected: (value) {
                                    if (value == 'delete') {
                                      _confirmDeleteSale(sale);
                                    }
                                  },
                                  itemBuilder: (context) => const [
                                    PopupMenuItem(
                                      value: 'delete',
                                      child: Row(
                                        children: [
                                          Icon(Icons.delete_outline, size: 18, color: Colors.red),
                                          SizedBox(width: 8),
                                          Text('Delete invoice'),
                                        ],
                                      ),
                                    ),
                                  ],
                                ),
                            ],
                          ),
                          onTap: () => _openDetail(sale.id),
                        );
                      },
                    ),
                  ),
            detail: workspace.selectedDetail != null ? const SalesDetailSheet() : null,
          ),
        ),
        _SalesPagination(workspace: workspace, onPage: controller.setPage),
      ],
    );
  }
}

class _SalesPagination extends StatelessWidget {
  const _SalesPagination({required this.workspace, required this.onPage});

  final SalesWorkspaceState workspace;
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
            Text('Page ${workspace.page} of ${workspace.totalPages} (${workspace.totalItems} sales)'),
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
