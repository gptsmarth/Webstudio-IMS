import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/connection/presentation/connection_controller.dart';
import '../config/app_config_provider.dart';
import 'api_client.dart';

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
  bool _running = false;

  void start() {
    if (_running) return;
    _running = true;
    _timer = Timer.periodic(const Duration(seconds: 15), (_) => _probe());
    unawaited(_probe());
  }

  void dispose() {
    _running = false;
    _timer?.cancel();
    _timer = null;
  }

  Future<void> _probe() async {
    if (!_running) return;
    final client = _ref.read(apiClientProvider);
    var healthy = await client.checkHealthLive();
    if (!_running) return;
    if (healthy) return;

    final repo = _ref.read(serverRepositoryProvider);
    final resolved = await repo.resolveSavedServerUrls();
    final config = _ref.read(appConfigProvider);
    final candidates = <String>{
      if (config.apiBaseUrl.isNotEmpty) config.apiBaseUrl,
      ...resolved,
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
