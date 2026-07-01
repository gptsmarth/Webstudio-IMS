import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_spacing.dart';
import '../../../shared/widgets/placeholders.dart';
import '../../settings/data/settings_repository.dart';
import '../data/tally_repository.dart';

class TallyScreen extends ConsumerStatefulWidget {
  const TallyScreen({super.key});

  @override
  ConsumerState<TallyScreen> createState() => _TallyScreenState();
}

class _TallyScreenState extends ConsumerState<TallyScreen> {
  bool _actionInProgress = false;
  String? _actionMessage;

  Future<void> _runAction(String label, Future<Map<String, dynamic>> Function() action) async {
    setState(() {
      _actionInProgress = true;
      _actionMessage = null;
    });
    try {
      final result = await action();
      if (!mounted) return;
      setState(() {
        _actionInProgress = false;
        _actionMessage = result['message']?.toString() ?? '$label completed';
      });
      ref.invalidate(tallyStatusProvider);
      ref.invalidate(tallyDashboardProvider);
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _actionInProgress = false;
        _actionMessage = error.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final status = ref.watch(tallyStatusProvider);
    final dashboard = ref.watch(tallyDashboardProvider);
    final settings = ref.watch(settingsWorkspaceProvider);
    final repo = ref.read(tallyRepositoryProvider);

    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(tallyStatusProvider);
        ref.invalidate(tallyDashboardProvider);
        ref.invalidate(settingsWorkspaceProvider);
        await Future.wait([
          ref.read(tallyStatusProvider.future),
          ref.read(tallyDashboardProvider.future),
        ]);
      },
      child: ListView(
        padding: const EdgeInsets.all(AppSpacing.md),
        children: [
          if (_actionMessage != null) SuccessBanner(message: _actionMessage!),
          if (_actionInProgress) const LinearProgressIndicator(minHeight: 2),
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: [
              FilledButton.icon(
                onPressed: _actionInProgress ? null : () => _runAction('Sync', repo.triggerSync),
                icon: const Icon(Icons.sync, size: 18),
                label: const Text('Manual sync'),
              ),
              OutlinedButton.icon(
                onPressed: _actionInProgress ? null : () => _runAction('Retry', repo.retrySync),
                icon: const Icon(Icons.replay, size: 18),
                label: const Text('Retry sync'),
              ),
              OutlinedButton.icon(
                onPressed: _actionInProgress ? null : () => _runAction('Connection test', repo.testConnection),
                icon: const Icon(Icons.link, size: 18),
                label: const Text('Test connection'),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.lg),
          Text('Tally status', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: AppSpacing.sm),
          status.when(
            loading: () => const LinearProgressIndicator(),
            error: (e, _) => Text(e.toString()),
            data: (data) => _StatusCard(
              title: data.connectionHealth,
              lines: [
                'Connection: ${data.connectionStatus}',
                'Available: ${data.available ? 'Yes' : 'No'}',
                'Companies: ${data.connectedCompanies}',
                'Pending issues: ${data.pendingIssues}',
                'Last sync: ${data.lastSync?.split('T').first ?? '—'}',
                'Next sync: ${data.nextScheduledSync?.split('T').first ?? '—'}',
                if (data.lastError != null) 'Last error: ${data.lastError}',
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.lg),
          settings.when(
            loading: () => const SizedBox.shrink(),
            error: (_, __) => const SizedBox.shrink(),
            data: (workspace) => _StatusCard(
              title: workspace.tally.connectionStatus,
              lines: [
                'Host: ${workspace.tally.tallyHost}:${workspace.tally.tallyPort}',
                'Company: ${workspace.tally.tallyCompanyName ?? '—'}',
                'Enabled: ${workspace.tally.enabled ? 'Yes' : 'No'}',
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.lg),
          Text('Recent synchronizations', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: AppSpacing.sm),
          dashboard.when(
            loading: () => const LinearProgressIndicator(),
            error: (e, _) => Text(e.toString()),
            data: (data) {
              final recent = data['recent_synchronizations'];
              if (recent is! List || recent.isEmpty) {
                return const Text('No recent synchronizations');
              }
              return Column(
                children: recent.take(10).map((entry) {
                  final map = Map<String, dynamic>.from(entry as Map);
                  return ListTile(
                    title: Text(map['printed_invoice_number']?.toString() ?? map['sync_run_id']?.toString() ?? 'Sync'),
                    subtitle: Text(
                      '${map['status'] ?? '—'} · ${(map['started_at'] as String?)?.split('T').first ?? '—'}',
                    ),
                  );
                }).toList(),
              );
            },
          ),
        ],
      ),
    );
  }
}

class _StatusCard extends StatelessWidget {
  const _StatusCard({required this.title, required this.lines});

  final String title;
  final List<String> lines;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Chip(label: Text(title)),
            const SizedBox(height: AppSpacing.sm),
            for (final line in lines) Text(line),
          ],
        ),
      ),
    );
  }
}
