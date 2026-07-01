import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/device/device_permissions.dart';
import '../../../core/device/push_notification_service.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../shared/widgets/placeholders.dart';
import '../../../shared/widgets/workspace_layout.dart';
import '../domain/notification_models.dart';
import 'notifications_controller.dart';

class NotificationsScreen extends ConsumerStatefulWidget {
  const NotificationsScreen({super.key});

  @override
  ConsumerState<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends ConsumerState<NotificationsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      await ref.read(pushNotificationServiceProvider).initialize();
      await ref.read(devicePermissionsProvider).ensure(DevicePermissionKind.notifications);
      await ref.read(pushNotificationServiceProvider).requestPermission();
      await ref.read(notificationsWorkspaceProvider.notifier).load();
    });
  }

  @override
  Widget build(BuildContext context) {
    final workspace = ref.watch(notificationsWorkspaceProvider);
    final controller = ref.read(notificationsWorkspaceProvider.notifier);

    return Column(
      children: [
        WorkspaceToolbar(
          hintText: 'Search notifications…',
          onSearchChanged: controller.setSearch,
          onRefresh: controller.load,
          loading: workspace.loading,
        ),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
          child: Row(
            children: [
              FilterChip(
                label: Text('All (${workspace.items.length})'),
                selected: workspace.severityFilter == null,
                onSelected: (_) => controller.setSeverity(null),
              ),
              const SizedBox(width: 8),
              FilterChip(
                label: Text('Unread (${workspace.unreadCount})'),
                selected: false,
                onSelected: (_) {},
              ),
              for (final severity in NotificationSeverity.values) ...[
                const SizedBox(width: 8),
                FilterChip(
                  label: Text(severity.name),
                  selected: workspace.severityFilter == severity,
                  onSelected: (_) => controller.setSeverity(severity),
                ),
              ],
            ],
          ),
        ),
        if (workspace.error != null)
          ErrorBanner(message: workspace.error!, onRetry: controller.load),
        Expanded(
          child: workspace.loading && workspace.visibleItems.isEmpty
              ? const WorkspaceLoadingList()
              : workspace.visibleItems.isEmpty
              ? const EmptyStateView(
                  icon: Icons.notifications_none_outlined,
                  title: 'No notifications',
                  message: 'You are all caught up. New alerts will appear here.',
                )
              : RefreshIndicator(
                  onRefresh: controller.load,
                  child: ListView.separated(
                    itemCount: workspace.visibleItems.length,
                    separatorBuilder: (_, __) => const Divider(height: 1),
                    itemBuilder: (context, index) {
                      final item = workspace.visibleItems[index];
                      return ListTile(
                        leading: Icon(
                          _severityIcon(item.severity),
                          color: _severityColor(context, item.severity),
                        ),
                        title: Text(item.title),
                        subtitle: Text('${item.description}\n${item.createdAt.split('T').first}'),
                        isThreeLine: true,
                        trailing: PopupMenuButton<String>(
                          onSelected: (action) async {
                            if (action == 'read') await controller.markRead(item.id);
                            if (action == 'resolve') await controller.resolve(item.id);
                          },
                          itemBuilder: (_) => [
                            if (!item.isRead)
                              const PopupMenuItem(value: 'read', child: Text('Mark read')),
                            if (!item.isResolved)
                              const PopupMenuItem(value: 'resolve', child: Text('Archive')),
                          ],
                        ),
                      );
                    },
                  ),
                ),
        ),
      ],
    );
  }

  IconData _severityIcon(NotificationSeverity severity) => switch (severity) {
        NotificationSeverity.error => Icons.error_outline,
        NotificationSeverity.warning => Icons.warning_amber_outlined,
        NotificationSeverity.info => Icons.info_outline,
      };

  Color _severityColor(BuildContext context, NotificationSeverity severity) => switch (severity) {
        NotificationSeverity.error => Theme.of(context).colorScheme.error,
        NotificationSeverity.warning => Colors.orange,
        NotificationSeverity.info => Theme.of(context).colorScheme.primary,
      };
}
