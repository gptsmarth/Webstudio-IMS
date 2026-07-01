import '../../../core/constants/api_paths.dart';
import '../../../core/errors/api_exception.dart';
import '../../../core/network/api_client.dart';
import '../data/server_preferences.dart';
import '../domain/server_models.dart';

class ServerRepository {
  ServerRepository({
    required ApiClient apiClient,
    required ServerPreferences preferences,
  })  : _api = apiClient,
        _prefs = preferences;

  final ApiClient _api;
  final ServerPreferences _prefs;

  List<SavedServer> savedServers() => _prefs.listSavedServers();

  Future<ConnectionTestResult> testConnection(String baseUrl) async {
    final normalized = baseUrl.trim().replaceAll(RegExp(r'/+$'), '');
    if (normalized.isEmpty) {
      return const ConnectionTestResult(
        success: false,
        url: '',
        errorMessage: 'Enter a server address.',
      );
    }

    final started = DateTime.now();
    try {
      final healthy = await _api.checkHealthLiveAt(normalized);
      if (!healthy) {
        return ConnectionTestResult(
          success: false,
          url: normalized,
          errorMessage: 'Server did not respond to health check.',
        );
      }

      final setup = await _api.getAt<SetupStatus>(
        normalized,
        ApiPaths.setupStatus,
        parser: (json) => SetupStatus.fromJson(json! as Map<String, dynamic>),
      );

      String? version;
      try {
        final versionData = await _api.getAt<Map<String, dynamic>>(
          normalized,
          ApiPaths.version,
          parser: (json) => Map<String, dynamic>.from(json! as Map),
        );
        version = versionData['backend_version'] as String?;
      } catch (_) {
        // Version endpoint is optional for connection test.
      }

      final latency = DateTime.now().difference(started).inMilliseconds;
      return ConnectionTestResult(
        success: true,
        url: normalized,
        latencyMs: latency,
        backendVersion: version,
        companyName: setup.companyName,
      );
    } on ApiException catch (error) {
      return ConnectionTestResult(
        success: false,
        url: normalized,
        errorMessage: error.message,
      );
    } catch (_) {
      return ConnectionTestResult(
        success: false,
        url: normalized,
        errorMessage: 'Could not connect to this address.',
      );
    }
  }

  Future<ConnectionTestResult?> discoverServer(List<String> candidates) async {
    for (final candidate in candidates) {
      final result = await testConnection(candidate);
      if (result.success) {
        return result;
      }
    }
    return null;
  }

  Future<void> rememberSuccessfulConnection(ConnectionTestResult result) async {
    if (!result.success) return;
    await _prefs.saveServer(
      SavedServer(
        url: result.url,
        label: result.companyName,
        lastConnectedAt: DateTime.now(),
      ),
    );
  }

  Future<void> removeSavedServer(String url) => _prefs.removeServer(url);
}
