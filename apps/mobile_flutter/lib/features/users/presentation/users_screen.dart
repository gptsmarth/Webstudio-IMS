import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_spacing.dart';
import '../../../core/rbac/role_permissions.dart';
import '../../../shared/widgets/placeholders.dart';
import '../../../shared/widgets/workspace_layout.dart';
import '../../auth/presentation/auth_controller.dart';
import '../data/access_role_repository.dart';
import '../domain/user_models.dart';
import 'users_controller.dart';

class UsersScreen extends ConsumerStatefulWidget {
  const UsersScreen({super.key});

  @override
  ConsumerState<UsersScreen> createState() => _UsersScreenState();
}

class _UsersScreenState extends ConsumerState<UsersScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(usersWorkspaceProvider.notifier).load();
    });
  }

  void _openDetail(int userId) {
    ref.read(usersWorkspaceProvider.notifier).selectUser(userId);
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (_) => const _UserDetailSheet(),
    ).whenComplete(() => ref.read(usersWorkspaceProvider.notifier).selectUser(null));
  }

  @override
  Widget build(BuildContext context) {
    final workspace = ref.watch(usersWorkspaceProvider);
    final controller = ref.read(usersWorkspaceProvider.notifier);

    return Column(
      children: [
        WorkspaceToolbar(
          hintText: 'Search users…',
          onSearchChanged: controller.setSearch,
          onRefresh: controller.load,
          loading: workspace.loading,
        ),
        if (workspace.error != null)
          ErrorBanner(message: workspace.error!, onRetry: controller.load),
        Expanded(
          child: workspace.loading && workspace.items.isEmpty
              ? const WorkspaceLoadingList()
              : workspace.items.isEmpty
              ? const EmptyStateView(
                  icon: Icons.people_outline,
                  title: 'No users found',
                  message: 'Try adjusting your search or refresh the list.',
                )
              : RefreshIndicator(
                  onRefresh: controller.load,
                  child: ListView.separated(
                    itemCount: workspace.items.length,
                    separatorBuilder: (_, __) => const Divider(height: 1),
                    itemBuilder: (context, index) {
                      final user = workspace.items[index];
                      return ListTile(
                        title: Text(user.displayLabel),
                        subtitle: Text(
                          '${userRoleLabel(user.role)} · ${user.status}'
                          '${user.isLocked ? ' · Locked' : ''}',
                        ),
                        trailing: Chip(label: Text('${user.activeSessionCount} sessions')),
                        onTap: () => _openDetail(user.id),
                      );
                    },
                  ),
                ),
        ),
        if (workspace.totalPages > 1)
          SafeArea(
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                IconButton(
                  onPressed: workspace.filters.page > 1
                      ? () => controller.setPage(workspace.filters.page - 1)
                      : null,
                  icon: const Icon(Icons.chevron_left),
                ),
                Text('Page ${workspace.filters.page} of ${workspace.totalPages}'),
                IconButton(
                  onPressed: workspace.filters.page < workspace.totalPages
                      ? () => controller.setPage(workspace.filters.page + 1)
                      : null,
                  icon: const Icon(Icons.chevron_right),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _UserDetailSheet extends ConsumerWidget {
  const _UserDetailSheet();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final workspace = ref.watch(usersWorkspaceProvider);
    final detail = workspace.selectedDetail;
    if (detail == null) return const SizedBox.shrink();

    return DraggableScrollableSheet(
      initialChildSize: 0.72,
      minChildSize: 0.45,
      maxChildSize: 0.95,
      expand: false,
      builder: (context, scrollController) {
        return Material(
          child: workspace.detailLoading
              ? const Center(child: CircularProgressIndicator())
              : ListView(
                  controller: scrollController,
                  padding: const EdgeInsets.all(AppSpacing.xl),
                  children: [
                    Text(detail.summary.displayLabel, style: Theme.of(context).textTheme.titleLarge),
                    Text('@${detail.summary.username}', style: Theme.of(context).textTheme.bodySmall),
                    const SizedBox(height: AppSpacing.lg),
                    _InfoRow(label: 'Access', value: detail.accessLabel ?? userRoleLabel(detail.summary.role)),
                    _InfoRow(label: 'Status', value: detail.summary.status),
                    _InfoRow(label: 'Sessions', value: '${detail.sessions.length}'),
                    _InfoRow(label: 'Permissions', value: '${detail.permissions.length}'),
                    const Divider(height: 32),
                    Wrap(
                      spacing: AppSpacing.sm,
                      runSpacing: AppSpacing.sm,
                      children: [
                        if (detail.summary.isLocked)
                          OutlinedButton(
                            onPressed: () => ref.read(usersWorkspaceProvider.notifier).unlockUser(detail.summary.id),
                            child: const Text('Unlock'),
                          ),
                        if (detail.summary.status == 'active')
                          OutlinedButton(
                            onPressed: () => ref.read(usersWorkspaceProvider.notifier).disableUser(detail.summary.id),
                            child: const Text('Deactivate'),
                          )
                        else if (!detail.summary.isArchived)
                          OutlinedButton(
                            onPressed: () => ref.read(usersWorkspaceProvider.notifier).enableUser(detail.summary.id),
                            child: const Text('Activate'),
                          ),
                        if (!detail.summary.isArchived)
                          OutlinedButton(
                            onPressed: () => ref.read(usersWorkspaceProvider.notifier).archiveUser(detail.summary.id),
                            child: const Text('Archive'),
                          )
                        else
                          OutlinedButton(
                            onPressed: () => ref.read(usersWorkspaceProvider.notifier).restoreUser(detail.summary.id),
                            child: const Text('Restore'),
                          ),
                        OutlinedButton(
                          onPressed: () => _openChangeAccess(context, ref, detail),
                          child: const Text('Change access'),
                        ),
                        OutlinedButton(
                          onPressed: () async {
                            final password = await _promptPassword(context);
                            if (password != null) {
                              await ref.read(usersWorkspaceProvider.notifier).resetPassword(detail.summary.id, password);
                            }
                          },
                          child: const Text('Reset password'),
                        ),
                        OutlinedButton(
                          onPressed: () => ref.read(usersWorkspaceProvider.notifier).logoutAll(detail.summary.id),
                          child: const Text('Logout all sessions'),
                        ),
                      ],
                    ),
                    const Divider(height: 32),
                    Text('Sessions', style: Theme.of(context).textTheme.titleSmall),
                    const SizedBox(height: AppSpacing.sm),
                    for (final session in detail.sessions.take(5))
                      ListTile(
                        dense: true,
                        contentPadding: EdgeInsets.zero,
                        title: Text(session.deviceLabel ?? 'Session ${session.id}'),
                        subtitle: Text(session.lastUsedAt?.split('T').first ?? session.createdAt.split('T').first),
                      ),
                    const Divider(height: 32),
                    Text('Recent logins', style: Theme.of(context).textTheme.titleSmall),
                    const SizedBox(height: AppSpacing.sm),
                    for (final event in detail.loginEvents.take(5))
                      ListTile(
                        dense: true,
                        contentPadding: EdgeInsets.zero,
                        leading: Icon(
                          event.success ? Icons.check_circle_outline : Icons.cancel_outlined,
                          size: 18,
                        ),
                        title: Text(event.success ? 'Success' : event.failureReason ?? 'Failed'),
                        subtitle: Text(event.createdAt.split('T').first),
                      ),
                  ],
                ),
        );
      },
    );
  }
}

Future<void> _openChangeAccess(BuildContext context, WidgetRef ref, UserDetail detail) async {
  final permissions = effectivePermissions(ref.read(authControllerProvider).user);
  if (!permissions.contains('users:edit')) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('You do not have permission to change user access.')),
    );
    return;
  }

  final roles = await ref.read(accessRoleRepositoryProvider).listRoles();
  if (!context.mounted) return;

  var accessType = detail.customAccessRoleId != null ? 'custom' : 'builtin';
  var builtinRole = detail.summary.role;
  int? customRoleId = detail.customAccessRoleId;

  await showDialog<void>(
    context: context,
    builder: (dialogContext) => StatefulBuilder(
      builder: (context, setState) => AlertDialog(
        title: const Text('Change access'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButtonFormField<String>(
                value: accessType,
                decoration: const InputDecoration(labelText: 'Access type'),
                items: const [
                  DropdownMenuItem(value: 'builtin', child: Text('Built-in role')),
                  DropdownMenuItem(value: 'custom', child: Text('Custom access role')),
                ],
                onChanged: (value) => setState(() => accessType = value ?? 'builtin'),
              ),
              if (accessType == 'builtin')
                DropdownButtonFormField<String>(
                  value: builtinRole,
                  decoration: const InputDecoration(labelText: 'Built-in role'),
                  items: const [
                    DropdownMenuItem(value: 'admin', child: Text('Admin')),
                    DropdownMenuItem(value: 'salesperson', child: Text('Salesperson')),
                  ],
                  onChanged: (value) => setState(() => builtinRole = value ?? 'salesperson'),
                )
              else
                DropdownButtonFormField<int>(
                  value: customRoleId,
                  decoration: const InputDecoration(labelText: 'Custom role'),
                  items: [
                    for (final role in roles)
                      DropdownMenuItem(value: role.id, child: Text(role.name)),
                  ],
                  onChanged: (value) => setState(() => customRoleId = value),
                ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('Cancel')),
          FilledButton(
            onPressed: () async {
              final controller = ref.read(usersWorkspaceProvider.notifier);
              if (accessType == 'builtin') {
                await controller.assignBuiltinAccess(detail.summary.id, builtinRole);
              } else if (customRoleId != null) {
                await controller.assignCustomAccess(detail.summary.id, customRoleId!);
              }
              if (dialogContext.mounted) Navigator.pop(dialogContext);
            },
            child: const Text('Save'),
          ),
        ],
      ),
    ),
  );
}

Future<String?> _promptPassword(BuildContext context) async {
  final controller = TextEditingController();
  return showDialog<String>(
    context: context,
    builder: (context) => AlertDialog(
      title: const Text('Reset password'),
      content: TextField(
        controller: controller,
        obscureText: true,
        decoration: const InputDecoration(labelText: 'New password'),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
        FilledButton(onPressed: () => Navigator.pop(context, controller.text), child: const Text('Reset')),
      ],
    ),
  );
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
        children: [
          SizedBox(width: 110, child: Text(label, style: Theme.of(context).textTheme.bodySmall)),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }
}
