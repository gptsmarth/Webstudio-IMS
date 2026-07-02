import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/config/app_config.dart';
import '../../../core/config/app_config_provider.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/host_validation.dart';
import '../data/server_preferences.dart';
import '../data/server_repository.dart';
import '../domain/server_models.dart';

enum ConnectionPhase { searching, found, manual, testing }

class ServerConnectionState {
  const ServerConnectionState({
    this.phase = ConnectionPhase.searching,
    this.messageIndex = 0,
    this.manualUrl = '',
    this.errorMessage,
    this.lastResult,
    this.savedServers = const [],
    this.discoveredServers = const [],
    this.diagnosticStages = const [],
  });

  final ConnectionPhase phase;
  final int messageIndex;
  final String manualUrl;
  final String? errorMessage;
  final ConnectionTestResult? lastResult;
  final List<SavedServer> savedServers;
  final List<DiscoveredServer> discoveredServers;
  final List<ConnectionStageResult> diagnosticStages;

  ServerConnectionState copyWith({
    ConnectionPhase? phase,
    int? messageIndex,
    String? manualUrl,
    String? errorMessage,
    ConnectionTestResult? lastResult,
    List<SavedServer>? savedServers,
    List<DiscoveredServer>? discoveredServers,
    List<ConnectionStageResult>? diagnosticStages,
    bool clearError = false,
    bool clearResult = false,
    bool clearDiagnostics = false,
  }) {
    return ServerConnectionState(
      phase: phase ?? this.phase,
      messageIndex: messageIndex ?? this.messageIndex,
      manualUrl: manualUrl ?? this.manualUrl,
      errorMessage: clearError ? null : errorMessage ?? this.errorMessage,
      lastResult: clearResult ? null : lastResult ?? this.lastResult,
      savedServers: savedServers ?? this.savedServers,
      discoveredServers: discoveredServers ?? this.discoveredServers,
      diagnosticStages: clearDiagnostics ? const [] : diagnosticStages ?? this.diagnosticStages,
    );
  }
}

final serverPreferencesProvider = Provider<ServerPreferences>((ref) {
  return ServerPreferences(ref.watch(sharedPreferencesProvider));
});

final serverRepositoryProvider = Provider<ServerRepository>((ref) {
  return ServerRepository(
    apiClient: ref.watch(apiClientProvider),
    preferences: ref.watch(serverPreferencesProvider),
  );
});

final connectionControllerProvider =
    StateNotifierProvider<ConnectionController, ServerConnectionState>((ref) {
  return ConnectionController(ref);
});

class ConnectionController extends StateNotifier<ServerConnectionState> {
  ConnectionController(this._ref)
      : super(
          ServerConnectionState(
            manualUrl: _ref.read(appConfigProvider).apiBaseUrl,
            savedServers: _ref.read(serverRepositoryProvider).savedServers(),
          ),
        );

  final Ref _ref;
  Timer? _messageTimer;
  bool _cancelled = false;

  static const discoveryMessages = [
    'Searching your local network',
    'Looking for WEBSTUDIO Server',
    'Verifying API endpoint',
    'Almost ready',
  ];

  @override
  void dispose() {
    _cancelled = true;
    _messageTimer?.cancel();
    super.dispose();
  }

  Future<void> startAutoDiscovery() async {
    _cancelled = false;
    _messageTimer?.cancel();
    state = state.copyWith(
      phase: ConnectionPhase.searching,
      messageIndex: 0,
      clearError: true,
      clearResult: true,
      clearDiagnostics: true,
      discoveredServers: const [],
      savedServers: _ref.read(serverRepositoryProvider).savedServers(),
    );

    _messageTimer = Timer.periodic(const Duration(milliseconds: 1800), (_) {
      if (_cancelled) return;
      state = state.copyWith(
        messageIndex: (state.messageIndex + 1) % discoveryMessages.length,
      );
    });

    final repo = _ref.read(serverRepositoryProvider);

    final mdnsFuture = repo.discoverMdnsServers();
    final savedUrlsFuture = repo.resolveSavedServerUrls();
    final mdnsServers = await mdnsFuture;
    final savedUrls = await savedUrlsFuture;

    _messageTimer?.cancel();
    if (_cancelled) return;

    if (mdnsServers.isNotEmpty) {
      state = state.copyWith(
        phase: ConnectionPhase.manual,
        discoveredServers: mdnsServers,
        manualUrl: state.manualUrl.isNotEmpty ? state.manualUrl : AppConfig.defaultApiBaseUrl(),
      );
      return;
    }

    final candidates = <String>[
      ...savedUrls,
      ...repo.staticDiscoveryCandidates(),
    ];
    final probeResult = await repo.discoverServer(candidates);
    if (_cancelled) return;

    if (probeResult != null) {
      state = state.copyWith(
        phase: ConnectionPhase.manual,
        discoveredServers: [
          DiscoveredServer(
            id: 'probe-${probeResult.url}',
            serverName: probeResult.companyName ?? 'WEBSTUDIO Server',
            companyName: probeResult.companyName ?? 'WEBSTUDIO',
            backendVersion: probeResult.backendVersion ?? 'unknown',
            apiVersion: '1.0',
            buildVersion: '',
            environment: 'local',
            port: Uri.parse(probeResult.url).port,
            host: Uri.parse(probeResult.url).host,
            url: probeResult.url,
            lastSeen: DateTime.now(),
            status: 'online',
          ),
        ],
        manualUrl: probeResult.url,
      );
      return;
    }

    state = state.copyWith(
      phase: ConnectionPhase.manual,
      manualUrl: state.manualUrl.isNotEmpty ? state.manualUrl : AppConfig.defaultApiBaseUrl(),
    );
  }

  void cancelDiscovery() {
    _cancelled = true;
    _messageTimer?.cancel();
  }

  Future<ConnectionTestResult?> connectToUrl(String url) async {
    state = state.copyWith(
      phase: ConnectionPhase.testing,
      clearError: true,
      clearDiagnostics: true,
    );
    final repo = _ref.read(serverRepositoryProvider);
    final config = _ref.read(appConfigProvider.notifier);
    final client = _ref.read(apiClientProvider);

    try {
      final normalized = normalizeServerUrl(url);
      final result = await repo.testConnection(normalized);
      if (_cancelled) return null;

      state = state.copyWith(diagnosticStages: result.stages);

      if (result.success) {
        await config.setApiBaseUrl(result.url);
        client.updateConfig(_ref.read(appConfigProvider));
        await repo.rememberSuccessfulConnection(result);
        state = state.copyWith(
          phase: ConnectionPhase.found,
          lastResult: result,
          manualUrl: result.url,
          savedServers: repo.savedServers(),
        );
        return result;
      }

      state = state.copyWith(
        phase: ConnectionPhase.manual,
        manualUrl: normalized,
        errorMessage: result.errorMessage ?? 'Could not connect to this address.',
      );
      return null;
    } on HostValidationException catch (error) {
      state = state.copyWith(
        phase: ConnectionPhase.manual,
        manualUrl: url,
        errorMessage: error.message,
      );
      return null;
    }
  }

  Future<void> removeSaved(String url) async {
    await _ref.read(serverRepositoryProvider).removeSavedServer(url);
    state = state.copyWith(savedServers: _ref.read(serverRepositoryProvider).savedServers());
  }
}
