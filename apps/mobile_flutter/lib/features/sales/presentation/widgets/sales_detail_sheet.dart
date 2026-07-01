import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../audit/data/audit_repository.dart';
import '../../../audit/domain/audit_models.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../domain/sales_models.dart';
import '../sales_controller.dart';

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

  @override
  Widget build(BuildContext context) {
    final workspace = ref.watch(salesWorkspaceProvider);
    final detail = workspace.selectedDetail;
    if (detail == null) return const SizedBox.shrink();

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
                    Text(detail.soldAt.split('T').first, style: Theme.of(context).textTheme.bodySmall),
                    const Divider(height: 32),
                    const _SectionTitle('Timeline'),
                    _TimelineTile(label: 'Sale recorded', date: detail.createdAt),
                    _TimelineTile(label: 'Sold on', date: detail.soldAt),
                    const Divider(height: 32),
                    const _SectionTitle('Invoice'),
                    _InfoRow(label: 'Payment', value: detail.paymentMode ?? '—'),
                    _InfoRow(label: 'Amount', value: formatSaleAmount(detail.saleAmount)),
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
                    if (detail.saleSource == 'tally') ...[
                      const SizedBox(height: AppSpacing.md),
                      const _SectionTitle('Tally'),
                      _InfoRow(label: 'Company', value: detail.tallyCompanyName ?? '—'),
                      _InfoRow(label: 'Voucher', value: detail.tallyVoucherNumber ?? '—'),
                      _InfoRow(label: 'Printed invoice', value: detail.printedInvoiceNumber ?? '—'),
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
