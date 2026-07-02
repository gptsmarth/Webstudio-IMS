import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/offline/offline_providers.dart';
import '../../../core/rbac/dashboard_permissions.dart';
import '../../../core/rbac/role_permissions.dart';
import '../../../core/routing/app_routes.dart';
import '../../../core/theme/app_breakpoints.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../shared/widgets/placeholders.dart';
import '../../../shared/widgets/workspace_layout.dart';
import '../../auth/domain/auth_models.dart';
import '../../auth/presentation/auth_controller.dart';
import '../../notifications/data/notification_repository.dart';
import '../../inventory/presentation/inventory_controller.dart';
import '../../tally/data/tally_repository.dart';
import '../../tally/presentation/widgets/tally_operational_widgets.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboard = ref.watch(dashboardDataProvider);

        final permissions = effectivePermissions(ref.watch(authControllerProvider).user);
        final showInventoryDistribution = canViewDashboardWidget(permissions, 'dashboard:inventory_distribution');
        final showBrandDistribution = canViewDashboardWidget(permissions, 'dashboard:brand_distribution');
        final showTally = canViewDashboardWidget(permissions, 'dashboard:tally_status');
        final showNotifications = canViewDashboardWidget(permissions, 'dashboard:notifications');
        final showActivity = canViewDashboardWidget(permissions, 'dashboard:recent_activity');

    return dashboard.when(
      loading: () => const LoadingView(message: 'Loading dashboard…'),
      error: (error, _) => ErrorBanner(
        message: error.toString(),
        onRetry: () => ref.invalidate(dashboardDataProvider),
      ),
      data: (result) {
        final data = result.data;
        final snapshot = data.snapshot;
        final distribution = data.distribution;
        final activity = data.activity;
        final user = ref.watch(authControllerProvider).user;
        final welcomeName = _dashboardWelcomeName(user);

        final tally = ref.watch(tallyDashboardProvider);
        final notifications = ref.watch(_notificationSummaryProvider);

        return RefreshIndicator(
          onRefresh: () async {
            await ref.read(backgroundSyncCoordinatorProvider.notifier).syncNow();
            ref.invalidate(dashboardDataProvider);
          },
          child: ListView(
            padding: AppBreakpoints.pagePadding(context).copyWith(bottom: AppSpacing.xxxl),
            children: [
              FadeIn(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
              if (result.fromCache || result.isStale)
                Card(
                  color: Theme.of(context).colorScheme.secondaryContainer,
                  child: ListTile(
                    dense: true,
                    leading: const Icon(Icons.offline_pin_outlined),
                    title: Text(result.isStale ? 'Showing cached dashboard data' : 'Loaded from local cache'),
                    subtitle: Text(result.error ?? 'Will refresh automatically when online.'),
                  ),
                ),
              _WelcomeBanner(name: welcomeName),
              const SizedBox(height: AppSpacing.lg),
              if (showInventoryDistribution) ...[
              _MetricCard(
                title: 'Available stock',
                value: '${snapshot.totalAvailableInventory}',
                subtitle: 'Units in inventory · ${snapshot.asOf.split('T').first}',
              ),
              const SizedBox(height: AppSpacing.lg),
              WorkspaceSectionHeader(title: 'Stock by location'),
              const SizedBox(height: AppSpacing.sm),
              ...distribution.byLocation.take(8).map(
                    (group) => _DistributionRow(label: group.name, available: group.available, total: group.total),
                  ),
              ],
              if (showTally) ...[
                const SizedBox(height: AppSpacing.lg),
                tally.when(
                  loading: () => const SizedBox.shrink(),
                  error: (_, __) => const SizedBox.shrink(),
                  data: (dashboard) => TallyDashboardSummaryCard(
                    operational: dashboard.operational,
                    onTap: () => context.push(AppRoutes.tally),
                  ),
                ),
              ],
              if (showNotifications)
                notifications.when(
                  loading: () => const SizedBox.shrink(),
                  error: (_, __) => const SizedBox.shrink(),
                  data: (count) => Card(
                    child: ListTile(
                      leading: const Icon(Icons.notifications_outlined),
                      title: const Text('Notifications'),
                      subtitle: Text('$count unresolved'),
                    ),
                  ),
                ),
              if (showBrandDistribution) ...[
                const SizedBox(height: AppSpacing.lg),
                WorkspaceSectionHeader(title: 'Stock by brand'),
                const SizedBox(height: AppSpacing.sm),
                ...distribution.byBrand.take(8).map(
                      (group) => _DistributionRow(label: group.name, available: group.available, total: group.total),
                    ),
              ],
              if (showActivity) ...[
                const SizedBox(height: AppSpacing.lg),
                WorkspaceSectionHeader(title: 'Recent activity'),
                const SizedBox(height: AppSpacing.sm),
                if (activity.isEmpty)
                  const EmptyStateView(
                    icon: Icons.history,
                    title: 'No recent activity',
                    message: 'Audit events and system actions will appear here.',
                  )
                else
                  ...activity.map(
                    (entry) => Card(
                      child: ListTile(
                        dense: true,
                        title: Text(entry.description ?? entry.activityType.replaceAll('_', ' ')),
                        subtitle: Text(entry.actorDisplayName ?? 'System'),
                        trailing: Text(
                          entry.createdAt.split('T').first,
                          style: Theme.of(context).textTheme.labelSmall,
                        ),
                      ),
                    ),
                  ),
              ],
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

String _dashboardWelcomeName(AuthUser? user) {
  if (user == null) return 'there';
  final label = user.displayLabel.trim();
  if (label.isEmpty) return user.username;
  return label.split(RegExp(r'\s+')).first;
}

class _WelcomeBanner extends StatelessWidget {
  const _WelcomeBanner({required this.name});

  final String name;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      elevation: 0,
      color: theme.colorScheme.primaryContainer.withValues(alpha: 0.35),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xl, vertical: AppSpacing.lg),
        child: Row(
          children: [
            Icon(Icons.waving_hand_outlined, color: theme.colorScheme.primary, size: 28),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Welcome, $name',
                    style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    'Here is your store overview for today.',
                    style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({required this.title, required this.value, required this.subtitle});

  final String title;
  final String value;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.xl),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: AppSpacing.sm),
            Text(value, style: Theme.of(context).textTheme.headlineMedium),
            Text(subtitle, style: Theme.of(context).textTheme.labelSmall),
          ],
        ),
      ),
    );
  }
}

class _DistributionRow extends StatelessWidget {
  const _DistributionRow({required this.label, required this.available, required this.total});

  final String label;
  final int available;
  final int total;

  @override
  Widget build(BuildContext context) {
    final ratio = total == 0 ? 0.0 : available / total;
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis)),
              Text('$available available'),
            ],
          ),
          const SizedBox(height: 4),
          LinearProgressIndicator(value: ratio),
        ],
      ),
    );
  }
}

final _notificationSummaryProvider = FutureProvider.autoDispose<int>((ref) async {
  final result = await ref.watch(notificationRepositoryProvider).listNotifications(isResolved: false, pageSize: 1);
  return result.totalItems;
});
