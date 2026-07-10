import 'package:flutter/material.dart';

import '../../../../core/theme/app_spacing.dart';
import '../../domain/tally_models.dart';

class TallyOperationalMetricsGrid extends StatelessWidget {
  const TallyOperationalMetricsGrid({
    super.key,
    required this.operational,
    this.showSyncCheckpoint = false,
  });

  final TallyOperationalSummary operational;
  final bool showSyncCheckpoint;

  @override
  Widget build(BuildContext context) {
    final checkpoint = operational.syncCheckpoint;
    final items = <_MetricItem>[
      _MetricItem('Connected', operational.connectionLabel, highlight: operational.isConnected),
      _MetricItem('Auto sync', operational.autoSyncEnabled ? 'Enabled' : 'Disabled'),
      _MetricItem('Polling interval', operational.pollingIntervalLabel),
      _MetricItem('Last successful sync', _formatDateTime(operational.lastSuccessfulSyncAt)),
      _MetricItem('Last invoice imported', operational.lastInvoiceImported ?? '—'),
      _MetricItem('Last invoice date', operational.lastInvoiceDate ?? '—'),
      _MetricItem('Next scheduled sync', _formatDateTime(operational.nextScheduledSyncAt)),
      _MetricItem('Last sync duration', operational.lastSyncDurationLabel),
      _MetricItem('Imported today', '${operational.importedToday}'),
      _MetricItem('Imported this week', '${operational.importedThisWeek}'),
      _MetricItem('Imported this month', '${operational.importedThisMonth}'),
      _MetricItem('Total imported', '${operational.totalImported}'),
      _MetricItem('Scheduler status', operational.schedulerStatusLabel, wide: true),
      if (operational.pendingRetry && operational.retryCountdownLabel != null)
        _MetricItem('Retry countdown', operational.retryCountdownLabel!, warn: true),
      if (showSyncCheckpoint && checkpoint != null) ...[
        _MetricItem('Last imported voucher date', checkpoint.lastImportedVoucherDate ?? '—'),
        _MetricItem('Last processed GUID', checkpoint.lastProcessedGuid ?? '—'),
        _MetricItem('Last processed Master ID', checkpoint.lastProcessedMasterId ?? '—'),
        _MetricItem('Last processed voucher type', checkpoint.lastProcessedVoucherType ?? '—'),
        _MetricItem('Last printed invoice', checkpoint.lastProcessedInvoiceNumber ?? '—'),
        _MetricItem('Checkpoint sync', _formatDateTime(checkpoint.lastSuccessfulSyncAt)),
        _MetricItem('Scheduler state', checkpoint.schedulerStatusLabel, wide: true),
      ],
    ];

    return LayoutBuilder(
      builder: (context, constraints) {
        final crossAxisCount = constraints.maxWidth >= 720 ? 3 : 2;
        return GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: crossAxisCount,
            mainAxisExtent: 78,
            crossAxisSpacing: AppSpacing.sm,
            mainAxisSpacing: AppSpacing.sm,
          ),
          itemCount: items.length,
          itemBuilder: (context, index) => _MetricTile(item: items[index]),
        );
      },
    );
  }

  static String _formatDateTime(String? iso) {
    if (iso == null || iso.isEmpty) return '—';
    final parsed = DateTime.tryParse(iso);
    if (parsed == null) return iso.split('T').first;
    return '${parsed.year}-${parsed.month.toString().padLeft(2, '0')}-${parsed.day.toString().padLeft(2, '0')} '
        '${parsed.hour.toString().padLeft(2, '0')}:${parsed.minute.toString().padLeft(2, '0')}';
  }
}

class _MetricItem {
  const _MetricItem(this.label, this.value, {this.highlight = false, this.warn = false, this.wide = false});

  final String label;
  final String value;
  final bool highlight;
  final bool warn;
  final bool wide;
}

class _MetricTile extends StatelessWidget {
  const _MetricTile({required this.item});

  final _MetricItem item;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    Color? valueColor;
    if (item.highlight) {
      valueColor = theme.colorScheme.primary;
    } else if (item.warn) {
      valueColor = theme.colorScheme.error;
    }

    return Container(
      padding: const EdgeInsets.all(AppSpacing.sm),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: theme.dividerColor),
        color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.35),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            item.label.toUpperCase(),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: theme.textTheme.labelSmall?.copyWith(
              letterSpacing: 0.4,
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            item.value,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: theme.textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.w700,
              color: valueColor,
            ),
          ),
        ],
      ),
    );
  }
}

class TallyDashboardSummaryCard extends StatelessWidget {
  const TallyDashboardSummaryCard({
    super.key,
    required this.operational,
    this.onTap,
  });

  final TallyOperationalSummary operational;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    operational.isConnected ? Icons.link : Icons.link_off,
                    size: 20,
                    color: operational.isConnected
                        ? Theme.of(context).colorScheme.primary
                        : Theme.of(context).colorScheme.error,
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Text('Tally ERP', style: Theme.of(context).textTheme.titleMedium),
                  const Spacer(),
                  Chip(
                    label: Text(tallyHealthLabel(operational.syncHealth)),
                    visualDensity: VisualDensity.compact,
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.sm),
              _SummaryRow(label: 'Connected', value: operational.isConnected ? 'Yes' : 'No'),
              _SummaryRow(
                label: 'Last sync',
                value: TallyOperationalMetricsGrid._formatDateTime(operational.lastSuccessfulSyncAt),
              ),
              _SummaryRow(
                label: 'Pending retry',
                value: operational.pendingRetry ? (operational.retryCountdownLabel ?? 'Yes') : 'No',
              ),
              _SummaryRow(label: "Today's imports", value: '${operational.todaysImports}'),
            ],
          ),
        ),
      ),
    );
  }
}

class _SummaryRow extends StatelessWidget {
  const _SummaryRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        children: [
          Expanded(child: Text(label, style: Theme.of(context).textTheme.bodyMedium)),
          Text(value, style: Theme.of(context).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}
