import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/connectivity_provider.dart';
import '../../core/offline/offline_models.dart';
import '../../core/offline/offline_providers.dart';
import '../../core/theme/app_spacing.dart';

class OfflineBanner extends ConsumerStatefulWidget {
  const OfflineBanner({super.key, required this.child});

  final Widget child;

  @override
  ConsumerState<OfflineBanner> createState() => _OfflineBannerState();
}

class _OfflineBannerState extends ConsumerState<OfflineBanner> {
  bool? _lastOnline;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(backgroundSyncCoordinatorProvider.notifier).start();
    });
  }

  @override
  Widget build(BuildContext context) {
    ref.listen<AsyncValue<bool>>(connectivityProvider, (previous, next) {
      final online = next.maybeWhen(data: (value) => value, orElse: () => true);
      if (_lastOnline == false && online) {
        ref.read(backgroundSyncCoordinatorProvider.notifier).syncNow();
      }
      _lastOnline = online;
    });

    final online = ref.watch(connectivityProvider).maybeWhen(data: (value) => value, orElse: () => true);
    final sync = ref.watch(backgroundSyncCoordinatorProvider);

    return Column(
      children: [
        if (!online)
          Material(
            color: Theme.of(context).colorScheme.errorContainer,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg, vertical: AppSpacing.sm),
              child: Row(
                children: [
                  Icon(Icons.cloud_off_outlined, size: 18, color: Theme.of(context).colorScheme.error),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: Text(
                      'Offline mode — dashboard and inventory lookup use cached data.',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ),
                ],
              ),
            ),
          )
        else if (sync.syncing)
          Material(
            color: Theme.of(context).colorScheme.secondaryContainer,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg, vertical: AppSpacing.sm),
              child: Row(
                children: [
                  const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(child: Text('Syncing…', style: Theme.of(context).textTheme.bodySmall)),
                ],
              ),
            ),
          )
        else if (sync.pendingCount > 0 || sync.conflictCount > 0)
          Material(
            color: Theme.of(context).colorScheme.secondaryContainer,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg, vertical: AppSpacing.sm),
              child: Row(
                children: [
                  Icon(Icons.cloud_queue_outlined, size: 18, color: Theme.of(context).colorScheme.onSecondaryContainer),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(child: Text(_syncMessage(sync), style: Theme.of(context).textTheme.bodySmall)),
                  TextButton(
                    onPressed: () => ref.read(backgroundSyncCoordinatorProvider.notifier).syncNow(),
                    child: const Text('Sync'),
                  ),
                ],
              ),
            ),
          ),
        Expanded(child: widget.child),
      ],
    );
  }

  String _syncMessage(SyncWorkspaceState sync) {
    if (sync.conflictCount > 0) {
      return '${sync.conflictCount} sync conflict(s) need review. ${sync.pendingCount} pending operation(s).';
    }
    if (sync.pendingCount > 0) {
      return '${sync.pendingCount} operation(s) queued — will sync automatically.';
    }
    if (sync.isStale) return 'Cached data may be out of date. Tap Sync to refresh.';
    return 'Synchronizing…';
  }
}
