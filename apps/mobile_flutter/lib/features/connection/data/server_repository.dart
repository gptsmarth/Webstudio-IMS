import '../../../core/config/app_config.dart';
import '../../../core/network/connection_diagnostics.dart';
import '../../../core/network/host_validation.dart';
import '../../../core/network/mdns_discovery_service.dart';
import '../../../core/network/api_client.dart';
import '../data/server_preferences.dart';
import '../domain/server_models.dart';

class ServerRepository {
  ServerRepository({
    required ApiClient apiClient,
    required ServerPreferences preferences,
    MdnsDiscoveryService? mdnsDiscovery,
    ConnectionDiagnostics? diagnostics,
  })  : _prefs = preferences,
        _mdns = mdnsDiscovery ?? MdnsDiscoveryService(),
        _diagnostics = diagnostics ?? ConnectionDiagnostics(apiClient);

  final ServerPreferences _prefs;
  final MdnsDiscoveryService _mdns;
  final ConnectionDiagnostics _diagnostics;

  List<SavedServer> savedServers() => _prefs.listSavedServers();

  Future<List<DiscoveredServer>> discoverMdnsServers() => _mdns.discover();

  Future<ConnectionTestResult> testConnection(String baseUrl) {
    return _diagnostics.run(baseUrl);
  }

  Future<List<String>> resolveSavedServerUrls() async {
    final servers = savedServers();
    final urls = <String>[];
    for (final server in servers) {
      final hostname = server.hostname ?? extractHostnameFromUrl(server.url);
      final port = Uri.parse(server.url).port;
      if (hostname != null) {
        final resolution = await resolveServerHost(hostname, port: port == 0 ? 8000 : port);
        if (resolution.success && resolution.resolvedIp != null) {
          final refreshed = normalizeServerUrl(server.url);
          await _prefs.saveServer(
            server.copyWith(
              url: refreshed,
              hostname: hostname,
              currentIp: resolution.resolvedIp,
              lastSeenAt: DateTime.now(),
            ),
          );
          urls.add(refreshed);
          continue;
        }
      }
      urls.add(server.url);
    }
    return urls;
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
    final hostname = extractHostnameFromUrl(result.url);
    String? currentIp;
    if (hostname != null) {
      final resolution = await resolveServerHost(hostname);
      currentIp = resolution.resolvedIp;
    }
    await _prefs.saveServer(
      SavedServer(
        url: result.url,
        label: result.companyName,
        friendlyName: result.companyName,
        companyName: result.companyName,
        hostname: hostname,
        currentIp: currentIp,
        backendVersion: result.backendVersion,
        lastConnectedAt: DateTime.now(),
        lastSeenAt: DateTime.now(),
      ),
    );
  }

  Future<void> removeSavedServer(String url) => _prefs.removeServer(url);

  List<String> staticDiscoveryCandidates() => AppConfig.discoveryCandidates();
}
