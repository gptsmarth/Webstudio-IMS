import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../audit/data/audit_repository.dart';
import '../../../audit/domain/audit_models.dart';
import '../../../../core/rbac/role_permissions.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../auth/presentation/auth_controller.dart';
import '../../domain/sales_models.dart';
import '../../domain/sales_permissions.dart';
import '../sales_controller.dart';
import 'sale_cancel_dialog.dart';

class SalesDetailSheet extends ConsumerStatefulWidget {
  const SalesDetailSheet({super.key});

  @override
  ConsumerState<SalesDetailSheet> createState() => _SalesDetailSheetState();
}

class _SalesDetailSheetState extends ConsumerState<SalesDetailSheet> {
  List<AuditLogEntry>? _auditEntries;
  bool _auditLoading = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadAudit());
  }

  Future<void> _loadAudit() async {
    final detail = ref.read(salesWorkspaceProvider).selectedDetail;
    if (detail == null || detail.inventoryItemId == null) return;
    setState(() => _auditLoading = true);
    try {
      final entries = await ref.read(auditRepositoryProvider).listForInventoryItem(detail.inventoryItemId!);
      if (mounted) setState(() { _auditEntries = entries; _auditLoading = false; });
    } catch (_) {
      if (mounted) setState(() => _auditLoading = false);
    }
  }

  Future<void> _confirmDelete(SaleDetail detail) async {
    final reasonInput = await showSaleCancelDialogForDetail(context, detail);
    if (reasonInput == null || !mounted) return;

    final messenger = ScaffoldMessenger.of(context);
    final controller = ref.read(salesWorkspaceProvider.notifier);
    try {
      final result = await controller.cancelSale(
        detail.id,
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
      if (Navigator.of(context).canPop()) {
        Navigator.of(context).pop();
      }
    } catch (error) {
      messenger.showSnackBar(SnackBar(content: Text(error.toString())));
    }
  }

  @override
  Widget build(BuildContext context) {
    final workspace = ref.watch(salesWorkspaceProvider);
    final detail = workspace.selectedDetail;
    if (detail == null) return const SizedBox.shrink();

    final permissions = effectivePermissions(ref.watch(authControllerProvider).user);
    final canDelete = canDeleteSale(permissions, detail.inventoryItemId);
    final isMainAdmin = ref.watch(authControllerProvider).user?.role == 'main_admin';
    final invoiceStatusLabel = switch (detail.invoiceStatus) {
      'processed' => 'Processed',
      'processed_with_warnings' => 'Processed With Warnings',
      'skipped' => 'Skipped',
      'failed' => 'Failed',
      null => null,
      final other => other.replaceAll('_', ' '),
    };

    return DraggableScrollableSheet(
      initialChildSize: 0.78,
      minChildSize: 0.45,
      maxChildSize: 0.95,
      expand: false,
      builder: (context, scrollController) {
        return Material(
          borderRadius: const BorderRadius.vertical(top: Radius.circular(AppSpacing.radiusXl)),
          child: workspace.detailLoading
              ? const Center(child: CircularProgressIndicator())
              : ListView(
                  controller: scrollController,
                  padding: const EdgeInsets.all(AppSpacing.xl),
                  children: [
                    Center(
                      child: Container(
                        width: 40,
                        height: 4,
                        decoration: BoxDecoration(
                          color: Theme.of(context).dividerColor,
                          borderRadius: BorderRadius.circular(2),
                        ),
                      ),
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    Row(
                      children: [
                        Expanded(child: Text(detail.invoiceNumber, style: Theme.of(context).textTheme.titleLarge)),
                        Chip(label: Text(saleSourceLabel(detail.saleSource))),
                      ],
                    ),
                    if (detail.reviewRequired) ...[
                      const SizedBox(height: AppSpacing.md),
                      Card(
                        color: Theme.of(context).colorScheme.errorContainer.withValues(alpha: 0.35),
                        child: ListTile(
                          dense: true,
                          title: const Text('Review required'),
                          subtitle: Text(detail.reviewReason ?? 'This Tally invoice needs operator review.'),
                        ),
                      ),
                    ],
                    if (canDelete) ...[
                      const SizedBox(height: AppSpacing.md),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: OutlinedButton.icon(
                          onPressed: workspace.actionInProgress ? null : () => _confirmDelete(detail),
                          icon: const Icon(Icons.delete_outline, size: 18),
                          label: const Text('Delete invoice'),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: Theme.of(context).colorScheme.error,
                          ),
                        ),
                      ),
                    ],
                    Text(detail.soldAt.split('T').first, style: Theme.of(context).textTheme.bodySmall),
                    const Divider(height: 32),
                    const _SectionTitle('Timeline'),
                    _TimelineTile(label: 'Sale recorded', date: detail.createdAt),
                    _TimelineTile(label: 'Sold on', date: detail.soldAt),
                    const Divider(height: 32),
                    const _SectionTitle('Invoice'),
                    if (invoiceStatusLabel != null)
                      _InfoRow(label: 'Invoice status', value: invoiceStatusLabel),
                    _InfoRow(label: 'Payment', value: detail.paymentMode ?? '—'),
                    _InfoRow(label: 'Amount (incl. GST)', value: formatSaleAmount(detail.saleAmount)),
                    if (detail.saleAmountExcludingGst != null)
                      _InfoRow(
                        label: 'Amount excluding GST',
                        value: formatSaleAmount(detail.saleAmountExcludingGst),
                      ),
                    _InfoRow(label: 'Sold by', value: detail.recordedByDisplayName ?? '—'),
                    const SizedBox(height: AppSpacing.md),
                    const _SectionTitle('Customer'),
                    _InfoRow(label: 'Name', value: detail.customerName ?? '—'),
                    if (detail.notes != null && detail.notes!.isNotEmpty)
                      _InfoRow(label: 'Notes', value: detail.notes!),
                    const SizedBox(height: AppSpacing.md),
                    const _SectionTitle('Laptop'),
                    _InfoRow(label: 'Serial', value: detail.serialNumber),
                    _InfoRow(label: 'Brand', value: detail.brandName),
                    _InfoRow(label: 'Model', value: '${detail.modelNumber} · ${detail.modelName}'),
                    _InfoRow(label: 'Store', value: detail.locationName),
                    _InfoRow(label: 'Color', value: detail.color),
                    _InfoRow(label: 'Specs', value: detail.specsLabel),
                    if (isMainAdmin && detail.serialSourceLabel != null)
                      _InfoRow(label: 'Serial source', value: detail.serialSourceLabel!),
                    if (detail.trackedProducts.isNotEmpty) ...[
                      const SizedBox(height: AppSpacing.md),
                      const _SectionTitle('Tracked products'),
                      for (final line in detail.trackedProducts)
                        _InfoRow(
                          label: (line['product_name'] as String?) ?? 'Product',
                          value: (line['serial_number'] as String?) ?? '—',
                        ),
                    ],
                    if (detail.additionalProducts.isNotEmpty) ...[
                      const SizedBox(height: AppSpacing.md),
                      const _SectionTitle('Additional products'),
                      for (final line in detail.additionalProducts)
                        _InfoRow(
                          label: (line['stock_item_name'] as String?) ?? 'Item',
                          value: (line['quantity'] as String?) ?? '—',
                        ),
                    ],
                    if (detail.unmatchedSerializedItems.isNotEmpty) ...[
                      const SizedBox(height: AppSpacing.md),
                      const _SectionTitle('Unmatched serialized items'),
                      for (final line in detail.unmatchedSerializedItems)
                        _InfoRow(
                          label: (line['product_name'] as String?) ?? 'Item',
                          value: (line['serial_number'] as String?) ?? '—',
                        ),
                    ],
                    if (detail.saleSource == 'tally') ...[
                      const SizedBox(height: AppSpacing.md),
                      const _SectionTitle('Tally'),
                      _InfoRow(label: 'Company', value: detail.tallyCompanyName ?? '—'),
                      _InfoRow(label: 'Voucher', value: detail.tallyVoucherNumber ?? '—'),
                      _InfoRow(label: 'Printed invoice', value: detail.printedInvoiceNumber ?? '—'),
                      if (invoiceStatusLabel != null)
                        _InfoRow(label: 'Invoice status', value: invoiceStatusLabel),
                      if (isMainAdmin && detail.tallyVoucherGuid != null)
                        _InfoRow(label: 'Voucher GUID', value: detail.tallyVoucherGuid!),
                      if (isMainAdmin && detail.tallyMasterId != null)
                        _InfoRow(label: 'Master ID', value: detail.tallyMasterId!),
                    ],
                    const Divider(height: 32),
                    const _SectionTitle('Audit'),
                    if (_auditLoading) const LinearProgressIndicator(minHeight: 2),
                    if (!_auditLoading && (_auditEntries == null || _auditEntries!.isEmpty))
                      const Text('No audit entries for this sale item'),
                    for (final entry in _auditEntries ?? const <AuditLogEntry>[])
                      ListTile(
                        dense: true,
                        contentPadding: EdgeInsets.zero,
                        leading: const Icon(Icons.history, size: 18),
                        title: Text(entry.description),
                        subtitle: Text('${entry.operation} · ${entry.createdAt.split('T').first}'),
                      ),
                  ],
                ),
        );
      },
    );
  }
}

class _TimelineTile extends StatelessWidget {
  const _TimelineTile({required this.label, required this.date});

  final String label;
  final String date;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      dense: true,
      contentPadding: EdgeInsets.zero,
      leading: const Icon(Icons.circle, size: 10),
      title: Text(label),
      trailing: Text(date.split('T').first, style: Theme.of(context).textTheme.labelSmall),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.label);
  final String label;
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Text(label, style: Theme.of(context).textTheme.titleSmall),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});
  final String label;
  final String value;
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(width: 110, child: Text(label, style: Theme.of(context).textTheme.bodySmall)),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }
}
