import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/device/file_transfer_service.dart';
import '../../../core/rbac/role_permissions.dart';
import '../../../core/theme/app_spacing.dart';
import '../../auth/presentation/auth_controller.dart';
import '../../../shared/widgets/placeholders.dart';
import '../../../shared/widgets/scrollable_bottom_sheet.dart';
import '../../../shared/widgets/workspace_layout.dart';
import '../data/report_filter_reference.dart';
import '../domain/report_models.dart';
import 'reports_controller.dart';
import 'widgets/report_filters_sheet.dart';

class ReportsScreen extends ConsumerStatefulWidget {
  const ReportsScreen({super.key});

  @override
  ConsumerState<ReportsScreen> createState() => _ReportsScreenState();
}

class _ReportsScreenState extends ConsumerState<ReportsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final workspace = ref.read(reportsWorkspaceProvider);
      if (!workspace.hasPreviewed && !workspace.loading) {
        ref.read(reportsWorkspaceProvider.notifier).preview();
      }
    });
  }

  Future<void> _exportReport(String format) async {
    final file = await ref.read(reportsWorkspaceProvider.notifier).fetchExport(format: format);
    if (file == null || !mounted) return;
    final transfer = ref.read(fileTransferServiceProvider);
    await showScrollableBottomSheet<void>(
      context: context,
      title: 'Export report',
      children: [
        ListTile(
          leading: const Icon(Icons.save_alt),
          title: const Text('Save to device'),
          onTap: () async {
            Navigator.pop(context);
            await transfer.saveToDocuments(filename: file.filename, bytes: file.bytes);
            if (!context.mounted) return;
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('Saved ${file.filename}')),
            );
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
  }

  Future<void> _openFilters() async {
    final workspace = ref.read(reportsWorkspaceProvider);
    final reference = await ref.read(reportFilterReferenceProvider.future);
    if (!mounted) return;
    final result = await showReportFiltersSheet(
      context,
      reportType: workspace.reportType,
      initial: workspace.params,
      reference: reference,
    );
    if (result == null || !mounted) return;
    ref.read(reportsWorkspaceProvider.notifier).applyFilters(result);
  }

  @override
  Widget build(BuildContext context) {
    final workspace = ref.watch(reportsWorkspaceProvider);
    final controller = ref.read(reportsWorkspaceProvider.notifier);
    final permissions = effectivePermissions(ref.watch(authControllerProvider).user);
    final canExport = permissions.contains('reports:export');
    final filterCount = workspace.params.activeFilterCount(workspace.reportType);

    return WorkspaceBody(
      alignTop: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.fromLTRB(AppSpacing.md, AppSpacing.md, AppSpacing.md, AppSpacing.sm),
            child: Row(
              children: [
                for (final type in ReportType.values) ...[
                  ChoiceChip(
                    label: Text(type.label),
                    selected: workspace.reportType == type,
                    onSelected: workspace.loading
                        ? null
                        : (_) => controller.setReportType(type),
                  ),
                  const SizedBox(width: 8),
                ],
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
            child: LayoutBuilder(
              builder: (context, constraints) {
                final stacked = constraints.maxWidth < 420;
                final searchField = TextField(
                  decoration: const InputDecoration(
                    hintText: 'Search report…',
                    prefixIcon: Icon(Icons.search, size: 20),
                    isDense: true,
                  ),
                  onChanged: controller.setSearch,
                  onSubmitted: (_) => controller.preview(),
                );
                final filterButton = OutlinedButton.icon(
                  onPressed: workspace.loading ? null : _openFilters,
                  icon: Badge(
                    isLabelVisible: filterCount > 0,
                    label: Text('$filterCount'),
                    child: const Icon(Icons.tune, size: 18),
                  ),
                  label: const Text('Filters'),
                );
                final previewButton = FilledButton(
                  onPressed: workspace.loading ? null : controller.preview,
                  child: const Text('Preview'),
                );
                final exportButton = canExport
                    ? PopupMenuButton<String>(
                        tooltip: 'Export',
                        onSelected: _exportReport,
                        itemBuilder: (_) => const [
                          PopupMenuItem(value: 'xlsx', child: Text('Export XLSX')),
                          PopupMenuItem(value: 'pdf', child: Text('Export PDF')),
                        ],
                        icon: const Icon(Icons.download_outlined),
                      )
                    : null;

                if (stacked) {
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      searchField,
                      const SizedBox(height: AppSpacing.sm),
                      filterButton,
                      const SizedBox(height: AppSpacing.sm),
                      Row(
                        children: [
                          Expanded(child: previewButton),
                          if (exportButton != null) exportButton,
                        ],
                      ),
                    ],
                  );
                }

                return Row(
                  children: [
                    Expanded(child: searchField),
                    const SizedBox(width: 8),
                    filterButton,
                    const SizedBox(width: 8),
                    previewButton,
                    if (exportButton != null) exportButton,
                  ],
                );
              },
            ),
          ),
          if (workspace.loading) const LinearProgressIndicator(minHeight: 2),
          if (workspace.error != null)
            ErrorBanner(message: workspace.error!, onRetry: controller.preview),
          if (workspace.preview?.summary != null)
            Padding(
              padding: const EdgeInsets.all(AppSpacing.md),
              child: Text(
                _formatSummary(workspace.preview!.summary!),
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ),
          Expanded(
            child: workspace.loading && !workspace.hasPreviewed
                ? const WorkspaceLoadingList()
                : !workspace.hasPreviewed
                    ? EmptyStateView(
                        icon: Icons.assessment_outlined,
                        title: 'Preview a report',
                        message: workspace.error ?? 'Choose a report type and tap Preview to load data.',
                        actionLabel: 'Preview report',
                        onAction: workspace.loading ? null : controller.preview,
                      )
                    : _ReportTable(workspace: workspace),
          ),
          if (workspace.preview != null && workspace.preview!.totalPages > 1)
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.sm),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  IconButton(
                    onPressed: workspace.params.page > 1
                        ? () => controller.setPage(workspace.params.page - 1)
                        : null,
                    icon: const Icon(Icons.chevron_left),
                  ),
                  Flexible(
                    child: Text(
                      'Page ${workspace.preview!.page} of ${workspace.preview!.totalPages} '
                      '(${workspace.preview!.totalItems} rows)',
                      textAlign: TextAlign.center,
                    ),
                  ),
                  IconButton(
                    onPressed: workspace.params.page < workspace.preview!.totalPages
                        ? () => controller.setPage(workspace.params.page + 1)
                        : null,
                    icon: const Icon(Icons.chevron_right),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  String _formatSummary(Map<String, dynamic> summary) {
    final parts = summary.entries
        .where((entry) => entry.value != null)
        .map((entry) => '${entry.key.replaceAll('_', ' ')}: ${entry.value}')
        .toList();
    return parts.isEmpty ? 'Summary available' : parts.join(' · ');
  }
}

class _ReportTable extends StatelessWidget {
  const _ReportTable({required this.workspace});

  final ReportsWorkspaceState workspace;

  @override
  Widget build(BuildContext context) {
    final preview = workspace.preview!;
    final columns = reportColumns(workspace.reportType);
    final labels = reportColumnLabels(workspace.reportType);

    if (preview.rows.isEmpty) {
      return const EmptyStateView(
        icon: Icons.filter_list_off,
        title: 'No matching rows',
        message: 'Adjust your search or report filters and preview again.',
      );
    }

    return ListView.separated(
      padding: const EdgeInsets.only(bottom: AppSpacing.lg),
      itemCount: preview.rows.length,
      separatorBuilder: (_, __) => const Divider(height: 1),
      itemBuilder: (context, index) {
        final row = preview.rows[index];
        final primary = reportCellValue(row, columns.first);
        final subtitle = columns
            .skip(1)
            .take(3)
            .map((c) => '${labels[c]}: ${reportCellValue(row, c)}')
            .join(' · ');
        return ListTile(title: Text(primary), subtitle: Text(subtitle), isThreeLine: true);
      },
    );
  }
}
