import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'version_check_controller.dart';

/// Runs version checks every 24 hours while the app is in the foreground.
class VersionCheckLifecycleObserver extends ConsumerStatefulWidget {
  const VersionCheckLifecycleObserver({super.key, required this.child});

  final Widget child;

  @override
  ConsumerState<VersionCheckLifecycleObserver> createState() => _VersionCheckLifecycleObserverState();
}

class _VersionCheckLifecycleObserverState extends ConsumerState<VersionCheckLifecycleObserver>
    with WidgetsBindingObserver {
  Timer? _periodicTimer;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    WidgetsBinding.instance.addPostFrameCallback((_) => _runStartupCheck());
    _periodicTimer = Timer.periodic(const Duration(hours: 24), (_) => _runPeriodicCheck());
  }

  @override
  void dispose() {
    _periodicTimer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _runPeriodicCheck();
    }
  }

  Future<void> _runStartupCheck() async {
    if (!mounted) return;
    await ref.read(versionCheckControllerProvider.notifier).check(
          trigger: VersionCheckTrigger.startup,
          context: context,
        );
  }

  Future<void> _runPeriodicCheck() async {
    if (!mounted) return;
    await ref.read(versionCheckControllerProvider.notifier).check(
          trigger: VersionCheckTrigger.periodic,
          context: context,
        );
  }

  @override
  Widget build(BuildContext context) => widget.child;
}
