import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/device/device_permissions.dart';
import '../../../core/device/file_transfer_service.dart';
import '../../../core/rbac/mobile_navigation.dart';
import '../../../core/rbac/role_permissions.dart';
import '../../../core/theme/app_spacing.dart';
import '../../auth/presentation/auth_controller.dart';
import '../../settings/data/settings_repository.dart';
import '../../settings/domain/settings_models.dart';

class BackupScreen extends ConsumerStatefulWidget {
  const BackupScreen({super.key});

  @override
  ConsumerState<BackupScreen> createState() => _BackupScreenState();
}

class _BackupScreenState extends ConsumerState<BackupScreen> {
  bool _importing = false;

  Future<void> _importBackup() async {
    final permissions = ref.read(devicePermissionsProvider);
    if (!await permissions.ensure(DevicePermissionKind.storage)) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Storage permission is required to import backup files.')),
        );
      }
      return;
    }

    final picked = await ref.read(fileTransferServiceProvider).pickFile(
          allowedExtensions: const ['xml', 'tar', 'gz', 'tgz', 'zip'],
        );
    if (picked == null || !mounted) return;

    setState(() => _importing = true);
    try {
      final result = await ref.read(settingsRepositoryProvider).importBackupFile(
            filename: picked.name,
            bytes: picked.bytes,
          );
      if (!mounted) return;
      final label = result['backup_format_label'] as String? ?? 'Backup';
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Imported $label (${picked.name})')),
      );
      ref.invalidate(settingsWorkspaceProvider);
      ref.invalidate(recoveryCenterProvider);
      ref.invalidate(backupAdminDashboardProvider);
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.toString())));
      }
    } finally {
      if (mounted) setState(() => _importing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final permissions = effectivePermissions(ref.watch(authControllerProvider).user);
    final showBackupStatus = canViewBackup(permissions) && canViewAdminSettings(permissions);
    final showBackupDashboard = canViewBackup(permissions);
    final showRecovery = canViewRestore(permissions);
    final showImport = canExecuteRestore(permissions);

    final workspace = showBackupStatus ? ref.watch(settingsWorkspaceProvider) : null;
    final recovery = showRecovery ? ref.watch(recoveryCenterProvider) : null;
    final dashboard = showBackupDashboard ? ref.watch(backupAdminDashboardProvider) : null;

    return RefreshIndicator(
      onRefresh: () async {
        final futures = <Future<void>>[];
        if (showBackupStatus) {
          ref.invalidate(settingsWorkspaceProvider);
          futures.add(ref.read(settingsWorkspaceProvider.future));
        }
        if (showRecovery) {
          ref.invalidate(recoveryCenterProvider);
          futures.add(ref.read(recoveryCenterProvider.future));
        }
        if (showBackupDashboard) {
          ref.invalidate(backupAdminDashboardProvider);
          futures.add(ref.read(backupAdminDashboardProvider.future));
        }
        if (futures.isNotEmpty) await Future.wait(futures);
      },
      child: ListView(
        padding: const EdgeInsets.all(AppSpacing.md),
        children: [
          if (showImport) ...[
            Card(
              child: Padding(
                padding: const EdgeInsets.all(AppSpacing.md),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Import backup', style: Theme.of(context).textTheme.titleSmall),
                    const SizedBox(height: AppSpacing.sm),
                    const Text(
                      'Upload XML archives or compressed backup files to the same import endpoint as desktop.',
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    FilledButton.icon(
                      onPressed: _importing ? null : _importBackup,
                      icon: _importing
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.upload_file),
                      label: Text(_importing ? 'Importing…' : 'Choose file'),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: AppSpacing.lg),
          ],
          if (showBackupStatus && workspace != null) ...[
            Text('Backup status', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: AppSpacing.sm),
            workspace.when(
              loading: () => const LinearProgressIndicator(),
              error: (e, _) => Text(e.toString()),
              data: (data) => _StatusCard(
                title: data.backup.healthStatus,
                lines: [
                  'Folder: ${data.backup.backupFolder}',
                  'Retention: ${data.backup.retentionPolicy}',
                  'Database: ${formatBytes(data.backup.databaseSizeBytes)}',
                  'Last backup: ${data.backup.lastBackupAt?.split('T').first ?? '—'}',
                  'Next scheduled: ${data.backup.nextScheduledBackupAt?.split('T').first ?? '—'}',
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.lg),
          ],
          if (showRecovery && recovery != null) ...[
            Text('Recovery status', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: AppSpacing.sm),
            recovery.when(
              loading: () => const LinearProgressIndicator(),
              error: (e, _) => Text(e.toString()),
              data: (data) => _StatusCard(
                title: data.recoveryReadiness,
                lines: [
                  'System: ${data.systemHealth}',
                  'Database: ${data.databaseStatus}',
                  'Backup: ${data.backupStatus}',
                  'Storage: ${data.storageStatus}',
                  'Failed backups: ${data.failedBackupCount}',
                  'Last restore: ${data.lastRestoreAt?.split('T').first ?? '—'}',
                ],
                issues: data.healthIssues.map((i) => '${i.title}: ${i.message}').toList(),
              ),
            ),
            const SizedBox(height: AppSpacing.lg),
          ],
          if (showBackupDashboard && dashboard != null) ...[
            Text('Backup dashboard', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: AppSpacing.sm),
            dashboard.when(
              loading: () => const LinearProgressIndicator(),
              error: (e, _) => Text(e.toString()),
              data: (data) => _StatusCard(
                title: data.storageHealth,
                lines: [
                  'Folder: ${data.backupFolder}',
                  'Total backups: ${data.totalBackupCount}',
                  'Warnings: ${data.warningCount}',
                  'Failed: ${data.failedBackupCount}',
                  'Newest: ${data.newestBackupAt?.split('T').first ?? '—'}',
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _StatusCard extends StatelessWidget {
  const _StatusCard({
    required this.title,
    required this.lines,
    this.issues = const [],
  });

  final String title;
  final List<String> lines;
  final List<String> issues;

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
            if (issues.isNotEmpty) ...[
              const SizedBox(height: AppSpacing.sm),
              Text('Issues', style: Theme.of(context).textTheme.titleSmall),
              for (final issue in issues) Text('• $issue'),
            ],
          ],
        ),
      ),
    );
  }
}
