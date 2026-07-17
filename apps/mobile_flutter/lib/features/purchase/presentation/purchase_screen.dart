import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/routing/app_routes.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../shared/widgets/placeholders.dart';
import '../../../shared/widgets/workspace_layout.dart';
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

  @override
  Widget build(BuildContext context) {
    final queue = ref.watch(purchaseQueueProvider(_statusFilter));

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
                    itemBuilder: (context, index) => _QueueCard(item: items[index]),
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

class _QueueCard extends StatelessWidget {
  const _QueueCard({required this.item});

  final PurchaseQueueItem item;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
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
