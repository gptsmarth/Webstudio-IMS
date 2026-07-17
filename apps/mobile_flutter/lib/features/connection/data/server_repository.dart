import 'dart:async';

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

  static const _probeTimeout = Duration(seconds: 8);

  Future<ConnectionTestResult?> discoverServer(List<String> candidates) async {
    for (final candidate in candidates) {
      ConnectionTestResult result;
      try {
        result = await testConnection(candidate).timeout(_probeTimeout);
      } on TimeoutException {
        result = ConnectionTestResult(
          success: false,
          url: candidate,
          errorMessage: 'Server did not respond in time.',
        );
      }
      if (result.success) {
        return result;
      }
    }
    return null;
  }

  /// Silent LAN discovery for bootstrap / reconnect.
  ///
  /// Order: mDNS → saved servers → static shop candidates.
  /// Returns the first fully validated server URL, or null if nothing responds.
  Future<ConnectionTestResult?> discoverBestServer({
    String? preferredUrl,
    bool includeMdns = true,
  }) async {
    if (includeMdns) {
      try {
        final mdnsServers = await discoverMdnsServers();
        for (final server in mdnsServers) {
          final result = await discoverServer([server.url]);
          if (result != null) return result;
        }
      } catch (_) {
        // Fall through to HTTP candidate probes.
      }
    }

    final savedUrls = await resolveSavedServerUrls();
    final candidates = <String>{
      if (preferredUrl != null && preferredUrl.trim().isNotEmpty) preferredUrl.trim(),
      ...savedUrls,
      ...staticDiscoveryCandidates(),
    }.toList();
    return discoverServer(candidates);
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
