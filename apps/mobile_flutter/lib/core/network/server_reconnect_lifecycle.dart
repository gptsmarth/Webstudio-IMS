import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../network/server_reconnect_provider.dart';

/// Starts background server health polling for automatic reconnection.
class ServerReconnectLifecycleObserver extends ConsumerStatefulWidget {
  const ServerReconnectLifecycleObserver({super.key, required this.child});

  final Widget child;

  @override
  ConsumerState<ServerReconnectLifecycleObserver> createState() =>
      _ServerReconnectLifecycleObserverState();
}

class _ServerReconnectLifecycleObserverState extends ConsumerState<ServerReconnectLifecycleObserver>
    with WidgetsBindingObserver {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(serverReconnectProvider).start();
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      ref.read(serverReconnectProvider).start();
    }
  }

  @override
  Widget build(BuildContext context) => widget.child;
}
