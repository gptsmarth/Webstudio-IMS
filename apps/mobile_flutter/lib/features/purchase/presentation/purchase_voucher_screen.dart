import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/rbac/mobile_navigation.dart';
import '../../../core/rbac/role_permissions.dart';
import '../../../core/theme/app_spacing.dart';
import '../../auth/presentation/auth_controller.dart';
import '../../../shared/widgets/placeholders.dart';
import '../../../shared/widgets/workspace_layout.dart';
import '../data/purchase_repository.dart';
import '../domain/purchase_models.dart';
import 'purchase_screen.dart';
import 'widgets/purchase_import_sheet.dart';

class PurchaseVoucherScreen extends ConsumerWidget {
  const PurchaseVoucherScreen({super.key, required this.voucherId});

  final int voucherId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final voucher = ref.watch(purchaseVoucherProvider(voucherId));

    return voucher.when(
      loading: () => const LoadingView(message: 'Loading voucher…'),
      error: (error, _) => ErrorBanner(
        message: error.toString(),
        onRetry: () => ref.invalidate(purchaseVoucherProvider(voucherId)),
      ),
      data: (detail) => _VoucherBody(detail: detail),
    );
  }
}

class _VoucherBody extends ConsumerWidget {
  const _VoucherBody({required this.detail});

  final PurchaseVoucherDetail detail;

  void _refresh(WidgetRef ref) {
    ref.invalidate(purchaseVoucherProvider(detail.id));
    ref.invalidate(purchaseQueueProvider);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final permissions = effectivePermissions(ref.watch(authControllerProvider).user);
    final canIgnore = canImportPurchase(permissions) && detail.status != 'imported';
    return WorkspaceBody(
      alignTop: true,
      child: ListView(
        padding: const EdgeInsets.only(bottom: AppSpacing.xxl),
        children: [
          Row(
            children: [
              Expanded(
                child: Text('Purchase ${detail.voucherNumber}', style: theme.textTheme.titleMedium),
              ),
              PurchaseStatusChip(status: detail.status),
              if (canIgnore)
                IconButton(
                  icon: const Icon(Icons.block_outlined, size: 20),
                  tooltip: 'Ignore this purchase invoice',
                  onPressed: () => confirmIgnorePurchase(
                    context,
                    ref,
                    voucherId: detail.id,
                    label: detail.voucherNumber,
                    onDone: () {
                      if (Navigator.of(context).canPop()) {
                        Navigator.of(context).pop();
                      }
                    },
                  ),
                ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          WorkspaceCard(
            padding: const EdgeInsets.all(AppSpacing.md),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _kv(theme, 'Supplier', detail.supplierName ?? '—'),
                _kv(theme, 'Invoice no.', detail.invoiceNumber ?? '—'),
                _kv(theme, 'Reference', detail.referenceNumber ?? '—'),
                _kv(theme, 'Date', detail.voucherDate ?? '—'),
                _kv(theme, 'GUID', detail.voucherGuid),
                const Divider(),
                _kv(theme, 'CGST', formatMoney(detail.taxes.cgstAmount)),
                _kv(theme, 'SGST', formatMoney(detail.taxes.sgstAmount)),
                _kv(theme, 'IGST', formatMoney(detail.taxes.igstAmount)),
                _kv(theme, 'Cess', formatMoney(detail.taxes.cessAmount)),
                _kv(theme, 'Invoice total', formatMoney(detail.grandTotal)),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          Text('Products', style: theme.textTheme.titleSmall),
          const SizedBox(height: AppSpacing.sm),
          for (final group in detail.groups) ...[
            _GroupCard(
              detail: detail,
              group: group,
              onImported: () => _refresh(ref),
            ),
            const SizedBox(height: AppSpacing.sm),
          ],
        ],
      ),
    );
  }

  Widget _kv(ThemeData theme, String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(width: 110, child: Text(label, style: theme.textTheme.bodySmall)),
          Expanded(child: Text(value, style: theme.textTheme.bodyMedium)),
        ],
      ),
    );
  }
}

class _GroupCard extends ConsumerWidget {
  const _GroupCard({
    required this.detail,
    required this.group,
    required this.onImported,
  });

  final PurchaseVoucherDetail detail;
  final PurchaseModelGroup group;
  final VoidCallback onImported;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final permissions = effectivePermissions(ref.watch(authControllerProvider).user);
    final canImport = canImportPurchase(permissions);
    return WorkspaceCard(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(group.stockItemName, style: theme.textTheme.titleSmall),
                    const SizedBox(height: 2),
                    Text(
                      'Quantity ${group.quantity} · ${group.serials.length} serial(s)'
                      '${group.duplicateCount > 0 ? ' · ${group.duplicateCount} already added' : ''}',
                      style: theme.textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
              if (group.imported)
                const PurchaseStatusChip(status: 'imported')
              else if (canImport)
                FilledButton(
                  onPressed: () => showPurchaseImportSheet(
                    context,
                    ref,
                    voucher: detail,
                    group: group,
                    onImported: onImported,
                  ),
                  child: const Text('Import'),
                )
              else
                const Chip(
                  label: Text('View only'),
                  visualDensity: VisualDensity.compact,
                ),
            ],
          ),
          if (group.serials.isNotEmpty) ...[
            const SizedBox(height: AppSpacing.sm),
            Wrap(
              spacing: AppSpacing.xs,
              runSpacing: AppSpacing.xs,
              children: [
                for (final cell in group.serials)
                  Chip(
                    label: Text(cell.serialNumber),
                    backgroundColor: cell.isDuplicate
                        ? theme.colorScheme.errorContainer
                        : null,
                    visualDensity: VisualDensity.compact,
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
