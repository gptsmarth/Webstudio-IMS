import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/routing/app_routes.dart';
import '../../../core/theme/app_spacing.dart';
import '../../auth/presentation/auth_controller.dart';
import '../../settings/data/settings_repository.dart';
import '../data/tally_repository.dart';
import 'widgets/tally_operational_widgets.dart';

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

  Future<void> _refresh() async {
    ref.invalidate(tallyStatusProvider);
    ref.invalidate(tallyDashboardProvider);
    ref.invalidate(settingsWorkspaceProvider);
    await Future.wait([
      ref.read(tallyDashboardProvider.future),
      ref.read(tallyStatusProvider.future),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final dashboard = ref.watch(tallyDashboardProvider);
    final settings = ref.watch(settingsWorkspaceProvider);
    final repo = ref.read(tallyRepositoryProvider);

    return RefreshIndicator(
      onRefresh: _refresh,
      child: ListView(
        padding: const EdgeInsets.all(AppSpacing.md),
        children: [
          if (_actionMessage != null)
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.sm),
              child: MaterialBanner(
                content: Text(_actionMessage!),
                actions: [
                  TextButton(onPressed: () => setState(() => _actionMessage = null), child: const Text('Dismiss')),
                ],
              ),
            ),
          if (_actionInProgress) const LinearProgressIndicator(minHeight: 2),
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: [
              FilledButton.icon(
                onPressed: _actionInProgress ? null : () => _runAction('Sync', repo.triggerSync),
                icon: const Icon(Icons.sync, size: 18),
                label: const Text('Sync now'),
              ),
              OutlinedButton.icon(
                onPressed: _actionInProgress ? null : () => _runAction('Connection test', repo.testConnection),
                icon: const Icon(Icons.link, size: 18),
                label: const Text('Test connection'),
              ),
              OutlinedButton.icon(
                onPressed: () => context.push(AppRoutes.tallyHistory),
                icon: const Icon(Icons.history, size: 18),
                label: const Text('View sync history'),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.lg),
          Text('Synchronization status', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: AppSpacing.sm),
          dashboard.when(
            loading: () => const LinearProgressIndicator(),
            error: (error, _) => Text(error.toString()),
            data: (data) {
              final isMainAdmin =
                  ref.watch(authControllerProvider).user?.role == 'main_admin';
              return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  TallyOperationalMetricsGrid(
                    operational: data.operational,
                    showSyncCheckpoint: isMainAdmin,
                  ),
                  if (data.lastError != null) ...[
                    const SizedBox(height: AppSpacing.sm),
                    Text(
                      data.lastError!,
                      style: TextStyle(color: Theme.of(context).colorScheme.error),
                    ),
                  ],
                ],
              );
            },
          ),
          const SizedBox(height: AppSpacing.lg),
          Text('Connection settings', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: AppSpacing.sm),
          settings.when(
            loading: () => const SizedBox.shrink(),
            error: (_, __) => const SizedBox.shrink(),
            data: (workspace) {
              final tally = workspace.tally;
              return Card(
                child: Padding(
                  padding: const EdgeInsets.all(AppSpacing.md),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Workstation: ${tally.tallyHost}:${tally.tallyPort}'),
                      const SizedBox(height: 4),
                      Text('Company: ${tally.tallyCompanyName ?? '—'}'),
                      const SizedBox(height: 4),
                      Text('Auto sync: ${tally.enabled ? 'Enabled' : 'Disabled'}'),
                    ],
                  ),
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}
