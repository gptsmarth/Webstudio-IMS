import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/network/api_client.dart';
import '../../../core/routing/app_routes.dart';
import '../presentation/auth_controller.dart';

class SessionManager extends ConsumerStatefulWidget {
  const SessionManager({super.key, required this.child});

  final Widget child;

  @override
  ConsumerState<SessionManager> createState() => _SessionManagerState();
}

class _SessionManagerState extends ConsumerState<SessionManager> {
  Timer? _idleTimer;
  Timer? _refreshTimer;
  DateTime _lastActivity = DateTime.now();
  int _sessionTimeoutMinutes = 30;
  bool _refreshing = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadPolicy());
  }

  @override
  void dispose() {
    _idleTimer?.cancel();
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadPolicy() async {
    try {
      final policy = await ref.read(authRepositoryProvider).getSessionPolicy();
      if (!mounted) return;
      setState(() => _sessionTimeoutMinutes = policy.sessionTimeoutMinutes);
      _startTimers();
    } catch (_) {
      _startTimers();
    }
  }

  void _startTimers() {
    if (!mounted) return;
    _idleTimer?.cancel();
    _refreshTimer?.cancel();
    _idleTimer = Timer.periodic(const Duration(seconds: 30), (_) => _checkIdle());
    _refreshTimer = Timer.periodic(const Duration(seconds: 30), (_) => _refreshIfNeeded());
  }

  void _touchActivity() {
    _lastActivity = DateTime.now();
  }

  Future<void> _checkIdle() async {
    if (!mounted) return;
    final idleMs = Duration(minutes: _sessionTimeoutMinutes < 5 ? 5 : _sessionTimeoutMinutes).inMilliseconds;
    if (DateTime.now().difference(_lastActivity).inMilliseconds < idleMs) return;
    await ref.read(authControllerProvider.notifier).logout(sessionExpired: true);
    if (!mounted) return;
    context.go(AppRoutes.login);
  }

  Future<void> _refreshIfNeeded() async {
    if (!mounted || _refreshing) return;
    final storage = ref.read(secureTokenStorageProvider);
    final expiresAt = await storage.getAccessExpiresAt();
    if (!mounted) return;
    if (expiresAt == null) return;
    if (expiresAt - DateTime.now().millisecondsSinceEpoch > 60000) return;

    _refreshing = true;
    try {
      final renewed = await ref.read(authControllerProvider.notifier).refreshTokens();
      if (!mounted) return;
      if (!renewed) {
        context.go(AppRoutes.login);
      }
    } finally {
      _refreshing = false;
    }
  }

  @override
  Widget build(BuildContext context) {
    ref.listen(authControllerProvider, (previous, next) {
      if (next.status == AuthStatus.sessionExpired && context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Your session has expired. Please sign in again.')),
        );
      }
    });

    return Listener(
      onPointerDown: (_) => _touchActivity(),
      onPointerSignal: (_) => _touchActivity(),
      child: widget.child,
    );
  }
}
