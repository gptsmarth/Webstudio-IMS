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
    final banner = _buildBanner(context, online: online, sync: sync);

    return Column(
      children: [
        if (banner != null) banner,
        Expanded(child: widget.child),
      ],
    );
  }

  Widget? _buildBanner(BuildContext context, {required bool online, required SyncWorkspaceState sync}) {
    final theme = Theme.of(context);
    final pendingLabel = _pendingLabel(sync.pendingCount);

    if (!online && sync.pendingCount > 0) {
      return _bannerShell(
        context,
        color: theme.colorScheme.errorContainer,
        icon: Icons.cloud_off_outlined,
        iconColor: theme.colorScheme.error,
        title: 'Offline',
        subtitle: pendingLabel,
      );
    }

    if (!online) {
      return _bannerShell(
        context,
        color: theme.colorScheme.errorContainer,
        icon: Icons.cloud_off_outlined,
        iconColor: theme.colorScheme.error,
        title: 'Offline',
        subtitle: 'Dashboard and inventory lookup use cached data.',
      );
    }

    if (sync.lastError != null && !sync.syncing) {
      return _bannerShell(
        context,
        color: theme.colorScheme.errorContainer,
        icon: Icons.sync_problem_outlined,
        iconColor: theme.colorScheme.error,
        title: 'Unable to synchronize.',
        trailing: TextButton(
          onPressed: () => ref.read(backgroundSyncCoordinatorProvider.notifier).syncNow(),
          child: const Text('Retry'),
        ),
      );
    }

    if (sync.syncing) {
      final progress = sync.syncTotal > 0 ? '${sync.syncCompleted}/${sync.syncTotal}' : null;
      return _bannerShell(
        context,
        color: theme.colorScheme.secondaryContainer,
        iconWidget: const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
        title: 'Syncing…',
        subtitle: progress,
      );
    }

    if (sync.syncSuccessVisible && sync.syncTotal > 0) {
      return _bannerShell(
        context,
        color: theme.colorScheme.tertiaryContainer,
        icon: Icons.check_circle_outline,
        iconColor: theme.colorScheme.tertiary,
        title: '${sync.syncCompleted}/${sync.syncTotal} synchronized',
      );
    }

    if (sync.pendingCount > 0 || sync.conflictCount > 0) {
      return _bannerShell(
        context,
        color: theme.colorScheme.secondaryContainer,
        icon: Icons.cloud_queue_outlined,
        iconColor: theme.colorScheme.onSecondaryContainer,
        title: sync.conflictCount > 0
            ? '${sync.conflictCount} sync conflict(s) need review'
            : pendingLabel,
        subtitle: sync.conflictCount > 0 ? pendingLabel : 'Will sync automatically when online',
        trailing: TextButton(
          onPressed: () => ref.read(backgroundSyncCoordinatorProvider.notifier).syncNow(),
          child: const Text('Sync'),
        ),
      );
    }

    return null;
  }

  String _pendingLabel(int count) {
    final noun = count == 1 ? 'change' : 'changes';
    return '$count pending $noun';
  }

  Widget _bannerShell(
    BuildContext context, {
    required Color color,
    IconData? icon,
    Color? iconColor,
    Widget? iconWidget,
    required String title,
    String? subtitle,
    Widget? trailing,
  }) {
    return Material(
      color: color,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg, vertical: AppSpacing.sm),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (iconWidget != null)
              iconWidget
            else if (icon != null)
              Icon(icon, size: 18, color: iconColor),
            const SizedBox(width: AppSpacing.sm),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: Theme.of(context).textTheme.bodySmall?.copyWith(fontWeight: FontWeight.w600)),
                  if (subtitle != null && subtitle.isNotEmpty)
                    Text(subtitle, style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
            ),
            if (trailing != null) trailing,
          ],
        ),
      ),
    );
  }
}
