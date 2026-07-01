import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/rbac/mobile_navigation.dart';
import '../../../core/rbac/role_permissions.dart';
import '../../../core/config/app_config_provider.dart';
import '../../../core/device/device_permissions.dart';
import '../../../core/routing/app_routes.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../shared/widgets/workspace_layout.dart';
import '../../../core/theme/theme_mode_provider.dart';
import '../../auth/presentation/auth_controller.dart';
import '../data/settings_repository.dart';
import '../data/settings_write_repository.dart';
import '../domain/settings_models.dart';
import '../presentation/settings_write_panel.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  Map<DevicePermissionKind, bool> _permissionStatus = const {};
  String? _passwordPolicyMessage;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _refreshPermissions();
      _loadPasswordPolicy();
    });
  }

  Future<void> _loadPasswordPolicy() async {
    try {
      final policy = await ref.read(authRepositoryProvider).getPasswordRecoveryPolicy();
      if (mounted) setState(() => _passwordPolicyMessage = policy.message);
    } catch (_) {
      if (mounted) {
        setState(() => _passwordPolicyMessage = 'Contact your Main Administrator to reset your password.');
      }
    }
  }

  Future<void> _refreshPermissions() async {
    final permissions = ref.read(devicePermissionsProvider);
    final status = <DevicePermissionKind, bool>{};
    for (final kind in DevicePermissionKind.values) {
      status[kind] = await permissions.isGranted(kind);
    }
    if (mounted) setState(() => _permissionStatus = status);
  }

  Future<void> _requestPermission(DevicePermissionKind kind) async {
    await ref.read(devicePermissionsProvider).ensure(kind);
    await _refreshPermissions();
  }

  @override
  Widget build(BuildContext context) {
    final config = ref.watch(appConfigProvider);
    final themeMode = ref.watch(themeModeProvider);
    final user = ref.watch(authControllerProvider).user;
    final permissions = effectivePermissions(user);
    final canWrite = canWriteSettings(permissions);
    final isMainAdmin = user?.role == 'main_admin';

    return RefreshIndicator(
      onRefresh: () async {
        if (canViewAdminSettings(permissions)) {
          ref.invalidate(settingsWorkspaceProvider);
          await ref.read(settingsWorkspaceProvider.future);
        }
        await _loadPasswordPolicy();
      },
      child: ListView(
        padding: const EdgeInsets.only(bottom: AppSpacing.xl),
        children: [
          if (user != null)
            ListTile(
              leading: const Icon(Icons.badge_outlined),
              title: Text(user.displayLabel),
              subtitle: Text(
                'Signed in as ${user.username} · ${user.role == 'main_admin' ? 'Main Admin' : '${permissions.length} permissions'}',
              ),
            ),
          const Divider(),
          ListTile(
            title: const Text('API server'),
            subtitle: Text(config.apiBaseUrl),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => context.push(AppRoutes.connection),
          ),
          const Divider(),
          Padding(
            padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.md, AppSpacing.lg, 0),
            child: WorkspaceSectionHeader(title: 'Appearance', subtitle: 'Light, dark, or follow system'),
          ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: SegmentedButton<ThemeMode>(
              segments: const [
                ButtonSegment(value: ThemeMode.system, label: Text('System')),
                ButtonSegment(value: ThemeMode.light, label: Text('Light')),
                ButtonSegment(value: ThemeMode.dark, label: Text('Dark')),
              ],
              selected: {themeMode},
              onSelectionChanged: (selection) {
                final mode = selection.first;
                final mapped = switch (mode) {
                  ThemeMode.dark => AppThemeMode.dark,
                  ThemeMode.light => AppThemeMode.light,
                  ThemeMode.system => AppThemeMode.system,
                };
                ref.read(themeModeProvider.notifier).setMode(mapped);
              },
            ),
          ),
          const Divider(),
          ListTile(
            leading: const Icon(Icons.lock_outline),
            title: const Text('Password'),
            subtitle: Text(
              _passwordPolicyMessage ??
                  'Contact your Main Administrator to reset your password.',
            ),
            onTap: () {
              final message = _passwordPolicyMessage ??
                  'Password recovery is not available for this account. Contact your Main Administrator to reset your password.';
              ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
            },
          ),
          const Divider(),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
            child: Text('Device permissions', style: Theme.of(context).textTheme.titleSmall),
          ),
          for (final kind in DevicePermissionKind.values)
            ListTile(
              leading: Icon(_permissionIcon(kind)),
              title: Text(_permissionLabel(kind)),
              subtitle: Text(_permissionStatus[kind] == true ? 'Granted' : 'Not granted'),
              trailing: TextButton(
                onPressed: () => _requestPermission(kind),
                child: const Text('Request'),
              ),
            ),
          const Divider(),
          if (permissions.contains('users:view') || isMainAdmin || permissions.contains('tally:view_status') || permissions.contains('audit:view') || canWrite) ...[
            Padding(
              padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.md, AppSpacing.lg, AppSpacing.sm),
              child: const WorkspaceSectionHeader(
                title: 'Administration',
                subtitle: 'Users, integrations, and system configuration',
              ),
            ),
            Card(
              margin: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
              clipBehavior: Clip.antiAlias,
              child: Column(
                children: [
            if (permissions.contains('users:view'))
              WorkspaceNavTile(
                icon: Icons.people_outline,
                title: 'Users',
                subtitle: 'Accounts, sessions, and access',
                onTap: () => context.push(AppRoutes.settingsUsers),
              ),
            if (isMainAdmin) ...[
              const Divider(height: 1),
              WorkspaceNavTile(
                icon: Icons.shield_outlined,
                title: 'Access roles',
                subtitle: 'Custom permissions for each role',
                onTap: () => context.push(AppRoutes.settingsAccessRoles),
              ),
            ],
            if (permissions.contains('tally:view_status')) ...[
              const Divider(height: 1),
              WorkspaceNavTile(
                icon: Icons.sync_alt_outlined,
                title: 'Tally',
                subtitle: 'Connection status and sync',
                onTap: () => context.push(AppRoutes.settingsTally),
              ),
            ],
            if (permissions.contains('audit:view')) ...[
              const Divider(height: 1),
              WorkspaceNavTile(
                icon: Icons.history,
                title: 'Audit center',
                onTap: () => context.push(AppRoutes.settingsAudit),
              ),
            ],
            if (canWrite) ...[
              const Divider(height: 1),
              WorkspaceNavTile(
                icon: Icons.edit_outlined,
                title: 'Edit settings',
                subtitle: 'Company, Tally host, AI configuration',
                onTap: () => showSettingsWritePanel(context, ref),
              ),
            ],
            if (canAccessBackupModule(permissions)) ...[
              const Divider(height: 1),
              WorkspaceNavTile(
                icon: Icons.backup_outlined,
                title: 'Backup & recovery',
                onTap: () => context.push(AppRoutes.settingsBackup),
              ),
            ],
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.lg),
          ],
          if (canViewAdminSettings(permissions)) ...[
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
              child: Text('System status', style: Theme.of(context).textTheme.titleSmall),
            ),
            ref.watch(settingsWorkspaceProvider).when(
              loading: () => const LinearProgressIndicator(minHeight: 2),
              error: (error, _) => ListTile(title: Text(error.toString())),
              data: (data) => Column(
                children: [
                  _StatusTile(
                    icon: Icons.business_outlined,
                    title: 'Company',
                    subtitle: '${data.companyName} · v${data.systemVersion}',
                  ),
                  _StatusTile(
                    icon: Icons.smart_toy_outlined,
                    title: 'AI provider',
                    subtitle: _aiStatusLabel(data.integrations),
                  ),
                ],
              ),
            ),
            const Divider(),
          ],
          ListTile(
            leading: const Icon(Icons.logout),
            title: const Text('Sign out'),
            onTap: () async {
              await ref.read(authControllerProvider.notifier).logout();
              if (context.mounted) context.go(AppRoutes.login);
            },
          ),
        ],
      ),
    );
  }

  String _aiStatusLabel(IntegrationsSummary integrations) {
    if (!integrations.aiEnrichmentEnabled) return 'AI enrichment disabled';
    final gemini = integrations.aiProviderHealth
        .where((entry) => entry.provider == 'gemini')
        .toList();
    if (gemini.isEmpty) {
      return integrations.geminiConfigured ? 'Gemini configured' : 'Gemini not configured';
    }
    return 'Gemini ${gemini.first.status}';
  }

  String _permissionLabel(DevicePermissionKind kind) => switch (kind) {
        DevicePermissionKind.camera => 'Camera',
        DevicePermissionKind.storage => 'Photos & files',
        DevicePermissionKind.notifications => 'Notifications',
      };

  IconData _permissionIcon(DevicePermissionKind kind) => switch (kind) {
        DevicePermissionKind.camera => Icons.photo_camera_outlined,
        DevicePermissionKind.storage => Icons.folder_outlined,
        DevicePermissionKind.notifications => Icons.notifications_outlined,
      };
}

class _StatusTile extends StatelessWidget {
  const _StatusTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(icon),
      title: Text(title),
      subtitle: Text(subtitle),
      trailing: onTap != null ? const Icon(Icons.chevron_right) : null,
      onTap: onTap,
    );
  }
}
