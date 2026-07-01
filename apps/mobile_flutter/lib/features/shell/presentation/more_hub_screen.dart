import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/rbac/mobile_navigation.dart';
import '../../../core/rbac/role_permissions.dart';
import '../../../core/routing/app_routes.dart';
import '../../../core/theme/app_spacing.dart';
import '../../auth/presentation/auth_controller.dart';
import '../../../shared/widgets/placeholders.dart';
import '../../../shared/widgets/workspace_layout.dart';

class MoreHubScreen extends ConsumerWidget {
  const MoreHubScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final permissions = effectivePermissions(ref.watch(authControllerProvider).user);
    final items = <_HubItem>[];

    if (permissions.contains('reports:view')) {
      items.add(_HubItem(
        AppRoutes.reports,
        'Reports',
        'Inventory, sales, audit, and tally exports',
        Icons.assessment_outlined,
      ));
    }
    if (permissions.contains('notifications:view')) {
      items.add(_HubItem(
        AppRoutes.notifications,
        'Notifications',
        'Alerts and system messages',
        Icons.notifications_outlined,
      ));
    }
    if (permissions.contains('audit:view')) {
      items.add(_HubItem(
        AppRoutes.audit,
        'Audit center',
        'Security and activity history',
        Icons.fact_check_outlined,
      ));
    }
    if (permissions.contains('tally:view_status')) {
      items.add(_HubItem(
        AppRoutes.tally,
        'Tally sync',
        'Integration status and retries',
        Icons.sync_outlined,
      ));
    }
    if (canAccessBackupModule(permissions)) {
      items.add(_HubItem(
        AppRoutes.backup,
        'Backup',
        'Recovery and backup operations',
        Icons.backup_outlined,
      ));
    }

    if (items.isEmpty) {
      return const EmptyStateView(
        icon: Icons.more_horiz,
        title: 'Nothing here yet',
        message: 'Modules available to you appear in the bottom navigation or Settings.',
      );
    }

    return WorkspaceBody(
      alignTop: true,
      child: ListView(
        padding: const EdgeInsets.only(bottom: AppSpacing.xxl),
        children: [
          const WorkspaceSectionHeader(
            title: 'More',
            subtitle: 'Reports, notifications, and operations',
          ),
          const SizedBox(height: AppSpacing.sm),
          Card(
            clipBehavior: Clip.antiAlias,
            child: Column(
              children: [
                for (var i = 0; i < items.length; i++) ...[
                  if (i > 0) const Divider(height: 1),
                  WorkspaceNavTile(
                    icon: items[i].icon,
                    title: items[i].title,
                    subtitle: items[i].subtitle,
                    onTap: () => context.push(items[i].route),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _HubItem {
  const _HubItem(this.route, this.title, this.subtitle, this.icon);

  final String route;
  final String title;
  final String subtitle;
  final IconData icon;
}
