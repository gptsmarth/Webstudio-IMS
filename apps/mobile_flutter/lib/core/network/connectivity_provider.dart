import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final connectivityProvider = StreamProvider<bool>((ref) async* {
  final connectivity = Connectivity();
  yield await _isOnline(connectivity);
  await for (final results in connectivity.onConnectivityChanged) {
    yield _hasConnection(results);
  }
});

Future<bool> _isOnline(Connectivity connectivity) async {
  final results = await connectivity.checkConnectivity();
  return _hasConnection(results);
}

bool _hasConnection(List<ConnectivityResult> results) {
  if (results.isEmpty) return true;
  return results.any(
    (result) =>
        result == ConnectivityResult.mobile ||
        result == ConnectivityResult.wifi ||
        result == ConnectivityResult.ethernet ||
        result == ConnectivityResult.vpn ||
        result == ConnectivityResult.other,
  );
}

/// Fast connectivity probe with timeout — avoids hanging bootstrap on iOS simulators.
Future<bool> checkNetworkAvailable({Duration timeout = const Duration(seconds: 3)}) async {
  try {
    final results = await Connectivity()
        .checkConnectivity()
        .timeout(timeout);
    return _hasConnection(results);
  } catch (_) {
    // If the OS probe stalls, fall through to the server health check.
    return true;
  }
}
