import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/constants/api_paths.dart';
import '../../../core/network/api_client.dart';
import '../domain/settings_models.dart';

class SettingsRepository {
  SettingsRepository(this._api);

  final ApiClient _api;

  Future<SettingsWorkspaceSummary> getWorkspace() async {
    return _api.get(
      ApiPaths.settings,
      parser: (json) => SettingsWorkspaceSummary.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<RecoveryCenterSummary> getRecoveryCenter() async {
    return _api.get(
      ApiPaths.settingsRecoveryCenter,
      parser: (json) => RecoveryCenterSummary.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<BackupAdminDashboardSummary> getBackupAdminDashboard() async {
    return _api.get(
      ApiPaths.settingsBackupsAdminDashboard,
      parser: (json) => BackupAdminDashboardSummary.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<TallyStatusSummary> getTallyStatus() async {
    return _api.get(
      ApiPaths.tallyStatus,
      parser: (json) => TallyStatusSummary.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<Map<String, dynamic>> getTallyDashboard() async {
    return _api.get(
      ApiPaths.tallyDashboard,
      parser: (json) => Map<String, dynamic>.from(json! as Map),
    );
  }

  Future<Map<String, dynamic>> importBackupFile({
    required String filename,
    required List<int> bytes,
  }) async {
    return _api.postMultipart(
      path: ApiPaths.settingsBackupsImport,
      fields: const {},
      files: {
        'file': MultipartFile.fromBytes(bytes, filename: filename),
      },
      parser: (json) => Map<String, dynamic>.from(json! as Map),
    );
  }
}

final settingsRepositoryProvider = Provider<SettingsRepository>((ref) {
  return SettingsRepository(ref.watch(apiClientProvider));
});

final settingsWorkspaceProvider = FutureProvider.autoDispose<SettingsWorkspaceSummary>((ref) async {
  return ref.watch(settingsRepositoryProvider).getWorkspace();
});

final recoveryCenterProvider = FutureProvider.autoDispose<RecoveryCenterSummary>((ref) async {
  return ref.watch(settingsRepositoryProvider).getRecoveryCenter();
});

final backupAdminDashboardProvider = FutureProvider.autoDispose<BackupAdminDashboardSummary>((ref) async {
  return ref.watch(settingsRepositoryProvider).getBackupAdminDashboard();
});

final tallyStatusProvider = FutureProvider.autoDispose<TallyStatusSummary>((ref) async {
  return ref.watch(settingsRepositoryProvider).getTallyStatus();
});
