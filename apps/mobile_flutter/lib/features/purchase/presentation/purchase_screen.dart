import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/rbac/mobile_navigation.dart';
import '../../../core/rbac/role_permissions.dart';
import '../../../core/routing/app_routes.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../shared/widgets/placeholders.dart';
import '../../../shared/widgets/workspace_layout.dart';
import '../../auth/presentation/auth_controller.dart';
import '../data/purchase_repository.dart';
import '../domain/purchase_models.dart';

String purchaseStatusLabel(String status) => switch (status) {
      'imported' => 'Imported',
      'partially_imported' => 'Partially imported',
      _ => 'Pending',
    };

String formatMoney(double? value) {
  if (value == null) return '—';
  return value.toStringAsFixed(2);
}

/// Warn, then tombstone a fetched purchase voucher so it disappears from the
/// queue and is never re-fetched. Refreshes the queue on success.
Future<void> confirmIgnorePurchase(
  BuildContext context,
  WidgetRef ref, {
  required int voucherId,
  required String label,
  VoidCallback? onDone,
}) async {
  final messenger = ScaffoldMessenger.of(context);
  final confirmed = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: const Text('Ignore this purchase invoice?'),
      content: Text(
        'Purchase $label will be removed from the queue and will NOT be fetched '
        'again on future Tally syncs. Any inventory already imported from it is '
        'kept. This does not change anything in Tally.',
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(ctx).pop(false),
          child: const Text('Cancel'),
        ),
        FilledButton(
          style: FilledButton.styleFrom(
            backgroundColor: Theme.of(ctx).colorScheme.error,
          ),
          onPressed: () => Navigator.of(ctx).pop(true),
          child: const Text('Ignore and remove'),
        ),
      ],
    ),
  );
  if (confirmed != true) return;
  try {
    await ref.read(purchaseRepositoryProvider).ignoreVoucher(voucherId);
    ref.invalidate(purchaseQueueProvider);
    messenger.showSnackBar(
      SnackBar(content: Text('Purchase $label removed from the queue.')),
    );
    onDone?.call();
  } catch (error) {
    messenger.showSnackBar(
      SnackBar(content: Text('Failed to ignore purchase: $error')),
    );
  }
}

class PurchaseStatusChip extends StatelessWidget {
  const PurchaseStatusChip({super.key, required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final color = switch (status) {
      'imported' => scheme.primary,
      'partially_imported' => scheme.tertiary,
      _ => scheme.outline,
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Text(
        purchaseStatusLabel(status),
        style: Theme.of(context).textTheme.labelSmall?.copyWith(color: color),
      ),
    );
  }
}

class PurchaseScreen extends ConsumerStatefulWidget {
  const PurchaseScreen({super.key});

  @override
  ConsumerState<PurchaseScreen> createState() => _PurchaseScreenState();
}

class _PurchaseScreenState extends ConsumerState<PurchaseScreen> {
  String? _statusFilter;
  bool _backfilling = false;

  Future<void> _fetchOlder() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: DateTime(now.year, now.month - 3, 1),
      firstDate: DateTime(now.year - 5),
      lastDate: now,
      helpText: 'Fetch purchases from',
    );
    if (picked == null) return;
    final fromDate = '${picked.year.toString().padLeft(4, '0')}-'
        '${picked.month.toString().padLeft(2, '0')}-'
        '${picked.day.toString().padLeft(2, '0')}';
    if (!mounted) return;
    final messenger = ScaffoldMessenger.of(context);
    setState(() => _backfilling = true);
    try {
      final result =
          await ref.read(purchaseRepositoryProvider).backfill(fromDate: fromDate);
      ref.invalidate(purchaseQueueProvider);
      messenger.showSnackBar(
        SnackBar(
          content: Text(
            'Fetched ${result.fetched} invoice(s) since ${result.fromDate} — '
            '${result.newCount} new added to the queue.',
          ),
        ),
      );
    } catch (error) {
      messenger.showSnackBar(
        SnackBar(content: Text('Failed to fetch older purchases: $error')),
      );
    } finally {
      if (mounted) setState(() => _backfilling = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final queue = ref.watch(purchaseQueueProvider(_statusFilter));
    final permissions = effectivePermissions(ref.watch(authControllerProvider).user);
    final canView = canViewPurchaseModule(permissions);
    final canImport = canImportPurchase(permissions);

    return WorkspaceBody(
      alignTop: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const WorkspaceSectionHeader(
            title: 'Purchase import queue',
            subtitle:
                'Tally purchase vouchers awaiting review. Nothing enters inventory automatically.',
          ),
          if (canView) ...[
            const SizedBox(height: AppSpacing.sm),
            Align(
              alignment: Alignment.centerLeft,
              child: OutlinedButton.icon(
                onPressed: _backfilling ? null : _fetchOlder,
                icon: const Icon(Icons.history, size: 18),
                label: Text(_backfilling ? 'Fetching…' : 'Fetch older purchases'),
              ),
            ),
          ],
          const SizedBox(height: AppSpacing.sm),
          Wrap(
            spacing: AppSpacing.sm,
            children: [
              for (final entry in const [
                (null, 'All'),
                ('pending', 'Pending'),
                ('partially_imported', 'Partial'),
                ('imported', 'Imported'),
              ])
                ChoiceChip(
                  label: Text(entry.$2),
                  selected: _statusFilter == entry.$1,
                  onSelected: (_) => setState(() => _statusFilter = entry.$1),
                ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          Expanded(
            child: queue.when(
              loading: () => const WorkspaceLoadingList(),
              error: (error, _) => ErrorBanner(
                message: error.toString(),
                onRetry: () => ref.invalidate(purchaseQueueProvider(_statusFilter)),
              ),
              data: (items) {
                if (items.isEmpty) {
                  return const EmptyStateView(
                    icon: Icons.shopping_cart_outlined,
                    title: 'No purchase vouchers',
                    message:
                        'Purchase vouchers appear here automatically after a Tally Day Book sync.',
                  );
                }
                return RefreshIndicator(
                  onRefresh: () async => ref.invalidate(purchaseQueueProvider(_statusFilter)),
                  child: ListView.separated(
                    padding: const EdgeInsets.only(bottom: AppSpacing.xxl),
                    itemCount: items.length,
                    separatorBuilder: (_, __) => const SizedBox(height: AppSpacing.sm),
                    itemBuilder: (context, index) =>
                        _QueueCard(item: items[index], canImport: canImport),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _QueueCard extends ConsumerWidget {
  const _QueueCard({required this.item, required this.canImport});

  final PurchaseQueueItem item;
  final bool canImport;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final canIgnore = canImport && item.status != 'imported';
    return WorkspaceCard(
      padding: const EdgeInsets.all(AppSpacing.md),
      onTap: () => context.push('${AppRoutes.purchase}/${item.id}'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(item.supplierName ?? 'Unknown supplier',
                    style: theme.textTheme.titleSmall),
              ),
              PurchaseStatusChip(status: item.status),
              if (canIgnore)
                IconButton(
                  icon: const Icon(Icons.block_outlined, size: 18),
                  tooltip: 'Ignore this purchase invoice',
                  visualDensity: VisualDensity.compact,
                  onPressed: () => confirmIgnorePurchase(
                    context,
                    ref,
                    voucherId: item.id,
                    label: item.voucherNumber,
                  ),
                ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            'Voucher ${item.voucherNumber}'
            '${item.invoiceNumber != null ? ' · Inv ${item.invoiceNumber}' : ''}'
            '${item.voucherDate != null ? ' · ${item.voucherDate}' : ''}',
            style: theme.textTheme.bodySmall,
          ),
          const SizedBox(height: AppSpacing.sm),
          Row(
            children: [
              Expanded(
                child: Text('Total ${formatMoney(item.grandTotal)}',
                    style: theme.textTheme.bodyMedium),
              ),
              Text('${item.importedGroupCount}/${item.groupCount} imported',
                  style: theme.textTheme.bodySmall),
            ],
          ),
        ],
      ),
    );
  }
}
