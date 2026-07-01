import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/constants/api_paths.dart';
import '../../../core/network/api_client.dart';

class SettingsWriteRepository {
  SettingsWriteRepository(this._api);

  final ApiClient _api;

  Future<Map<String, dynamic>> patchGeneral(Map<String, dynamic> data) async {
    return _api.patch(ApiPaths.settingsGeneral, data: data, parser: (j) => Map<String, dynamic>.from(j! as Map));
  }

  Future<Map<String, dynamic>> patchSecurity(Map<String, dynamic> data) async {
    return _api.patch(ApiPaths.settingsSecurity, data: data, parser: (j) => Map<String, dynamic>.from(j! as Map));
  }

  Future<Map<String, dynamic>> patchTally(Map<String, dynamic> data) async {
    return _api.patch(ApiPaths.settingsTally, data: data, parser: (j) => Map<String, dynamic>.from(j! as Map));
  }

  Future<Map<String, dynamic>> patchIntegrations(Map<String, dynamic> data) async {
    return _api.patch(ApiPaths.settingsIntegrations, data: data, parser: (j) => Map<String, dynamic>.from(j! as Map));
  }

  Future<Map<String, dynamic>> patchNotifications(Map<String, dynamic> data) async {
    return _api.patch(ApiPaths.settingsNotifications, data: data, parser: (j) => Map<String, dynamic>.from(j! as Map));
  }

  Future<List<Map<String, dynamic>>> listIntegrationKeys() async {
    return _api.get(
      ApiPaths.integrationKeys,
      parser: (json) {
        if (json is List) return json.whereType<Map<String, dynamic>>().map(Map<String, dynamic>.from).toList();
        return <Map<String, dynamic>>[];
      },
    );
  }
}

final settingsWriteRepositoryProvider = Provider<SettingsWriteRepository>((ref) {
  return SettingsWriteRepository(ref.watch(apiClientProvider));
});

bool canWriteSettings(List<String> permissions) =>
    permissions.contains('settings:modify') || permissions.contains('settings:write');

bool canManageIntegrationKeys(List<String> permissions) =>
    permissions.contains('settings:modify') || permissions.contains('admin:integration_keys');
