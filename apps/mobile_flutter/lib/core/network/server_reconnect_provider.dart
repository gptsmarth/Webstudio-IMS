import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/connection/presentation/connection_controller.dart';
import '../config/app_config_provider.dart';
import 'api_client.dart';
import 'connectivity_provider.dart';

/// Polls server health and refreshes hostname/IP before reconnect (M12D).
final serverReconnectProvider = Provider<ServerReconnectMonitor>((ref) {
  final monitor = ServerReconnectMonitor(ref);
  ref.onDispose(monitor.dispose);
  return monitor;
});

class ServerReconnectMonitor {
  ServerReconnectMonitor(this._ref);

  final Ref _ref;
  Timer? _timer;
  ProviderSubscription<AsyncValue<bool>>? _connectivitySub;
  bool _running = false;
  bool _wasOnline = true;

  void start() {
    if (_running) return;
    _running = true;
    _timer = Timer.periodic(const Duration(seconds: 15), (_) => _probe());
    _connectivitySub = _ref.listen<AsyncValue<bool>>(connectivityProvider, (previous, next) {
      final online = next.valueOrNull ?? true;
      if (!_wasOnline && online) {
        unawaited(_probe(fullDiscovery: true));
      }
      _wasOnline = online;
    });
    unawaited(_probe());
  }

  void dispose() {
    _running = false;
    _timer?.cancel();
    _timer = null;
    _connectivitySub?.close();
    _connectivitySub = null;
  }

  Future<void> _probe({bool fullDiscovery = false}) async {
    if (!_running) return;
    final client = _ref.read(apiClientProvider);
    var healthy = await client.checkHealthLive();
    if (!_running) return;
    if (healthy) return;

    final repo = _ref.read(serverRepositoryProvider);
    final config = _ref.read(appConfigProvider);

    if (fullDiscovery) {
      final best = await repo.discoverBestServer(preferredUrl: config.apiBaseUrl);
      if (!_running) return;
      if (best != null && best.success) {
        await _ref.read(appConfigProvider.notifier).setApiBaseUrl(best.url);
        client.updateConfig(_ref.read(appConfigProvider));
        await repo.rememberSuccessfulConnection(best);
      }
      return;
    }

    final resolved = await repo.resolveSavedServerUrls();
    final candidates = <String>{
      if (config.apiBaseUrl.isNotEmpty) config.apiBaseUrl,
      ...resolved,
      ...repo.staticDiscoveryCandidates(),
    };

    for (final url in candidates) {
      healthy = await client.checkHealthLiveAt(url);
      if (healthy) {
        await _ref.read(appConfigProvider.notifier).setApiBaseUrl(url);
        client.updateConfig(_ref.read(appConfigProvider));
        return;
      }
    }
  }
}
