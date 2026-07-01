import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/config/app_config.dart';
import '../../../core/config/app_config_provider.dart';
import '../../../core/network/api_client.dart';
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
  });

  final ConnectionPhase phase;
  final int messageIndex;
  final String manualUrl;
  final String? errorMessage;
  final ConnectionTestResult? lastResult;
  final List<SavedServer> savedServers;

  ServerConnectionState copyWith({
    ConnectionPhase? phase,
    int? messageIndex,
    String? manualUrl,
    String? errorMessage,
    ConnectionTestResult? lastResult,
    List<SavedServer>? savedServers,
    bool clearError = false,
    bool clearResult = false,
  }) {
    return ServerConnectionState(
      phase: phase ?? this.phase,
      messageIndex: messageIndex ?? this.messageIndex,
      manualUrl: manualUrl ?? this.manualUrl,
      errorMessage: clearError ? null : errorMessage ?? this.errorMessage,
      lastResult: clearResult ? null : lastResult ?? this.lastResult,
      savedServers: savedServers ?? this.savedServers,
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
      savedServers: _ref.read(serverRepositoryProvider).savedServers(),
    );

    _messageTimer = Timer.periodic(const Duration(milliseconds: 1800), (_) {
      if (_cancelled) return;
      state = state.copyWith(
        messageIndex: (state.messageIndex + 1) % discoveryMessages.length,
      );
    });

    final repo = _ref.read(serverRepositoryProvider);
    final config = _ref.read(appConfigProvider.notifier);
    final client = _ref.read(apiClientProvider);

    final candidates = <String>[
      ...AppConfig.discoveryCandidates(),
      ...state.savedServers.map((server) => server.url),
    ];

    final result = await repo.discoverServer(candidates);
    _messageTimer?.cancel();

    if (_cancelled) return;

    if (result != null) {
      await config.setApiBaseUrl(result.url);
      client.updateConfig(_ref.read(appConfigProvider));
      await repo.rememberSuccessfulConnection(result);
      state = state.copyWith(phase: ConnectionPhase.found, lastResult: result);
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
    state = state.copyWith(phase: ConnectionPhase.testing, clearError: true);
    final repo = _ref.read(serverRepositoryProvider);
    final config = _ref.read(appConfigProvider.notifier);
    final client = _ref.read(apiClientProvider);

    final result = await repo.testConnection(url);
    if (_cancelled) return null;

    if (result.success) {
      await config.setApiBaseUrl(result.url);
      client.updateConfig(_ref.read(appConfigProvider));
      await repo.rememberSuccessfulConnection(result);
      state = state.copyWith(phase: ConnectionPhase.found, lastResult: result, manualUrl: result.url);
      return result;
    }

    state = state.copyWith(
      phase: ConnectionPhase.manual,
      manualUrl: url,
      errorMessage: result.errorMessage ?? 'Could not connect to this address.',
    );
    return null;
  }

  Future<void> removeSaved(String url) async {
    await _ref.read(serverRepositoryProvider).removeSavedServer(url);
    state = state.copyWith(savedServers: _ref.read(serverRepositoryProvider).savedServers());
  }
}
