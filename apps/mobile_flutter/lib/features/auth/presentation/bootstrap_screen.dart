import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/config/app_config.dart';
import '../../../core/config/app_config_provider.dart';
import '../../../core/network/connectivity_provider.dart';
import '../../../core/network/api_client.dart';
import '../../../core/storage/hive_cache.dart';
import '../../../core/rbac/mobile_navigation.dart';
import '../../../core/rbac/role_permissions.dart';
import '../../../core/routing/app_routes.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../shared/widgets/webstudio_logo.dart';
import 'auth_controller.dart';

class BootstrapScreen extends ConsumerStatefulWidget {
  const BootstrapScreen({super.key});

  @override
  ConsumerState<BootstrapScreen> createState() => _BootstrapScreenState();
}

class _BootstrapScreenState extends ConsumerState<BootstrapScreen> {
  String _status = 'Starting WEBSTUDIO IMS…';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _start());
  }

  Future<void> _start() async {
    try {
      await _runBootstrap();
    } catch (error) {
      if (!mounted) return;
      setState(() => _status = 'Startup failed: $error');
      await Future<void>.delayed(const Duration(seconds: 2));
      if (!mounted) return;
      context.go(AppRoutes.connection);
    }
  }

  Future<void> _runBootstrap() async {
    final online = await checkNetworkAvailable();
    if (!mounted) return;

    if (!online) {
      final cachedUser = HiveCache.profile.get('current_user');
      final hasToken = await ref.read(authRepositoryProvider).restoreSession();
      if (!mounted) return;
      if (cachedUser != null || hasToken) {
        setState(() => _status = 'Offline mode — restoring cached session…');
        await _finishAuthBootstrap();
        return;
      }
      setState(() => _status = 'No network connection. Check Wi‑Fi or mobile data.');
      await Future<void>.delayed(const Duration(seconds: 2));
      if (!mounted) return;
      context.go(AppRoutes.connection);
      return;
    }

    setState(() => _status = 'Checking server connection…');
    final config = ref.read(appConfigProvider);
    final client = ref.read(apiClientProvider);

    if (AppConfig.shouldOpenConnectionSetupFirst(config.apiBaseUrl)) {
      setState(() => _status = 'Finding WEBSTUDIO Server on your Wi‑Fi…');
      if (!mounted) return;
      context.go(AppRoutes.connection);
      return;
    }

    final healthy = await client
        .checkHealthLive()
        .timeout(const Duration(seconds: 5), onTimeout: () => false);
    if (!mounted) return;

    if (!healthy) {
      setState(() => _status = 'Server unreachable. Opening connection setup…');
      await Future<void>.delayed(const Duration(milliseconds: 600));
      if (!mounted) return;
      context.go(AppRoutes.connection);
      return;
    }

    setState(() => _status = 'Restoring your session…');
    await _finishAuthBootstrap();
  }

  Future<void> _finishAuthBootstrap() async {
    await ref.read(authControllerProvider.notifier).bootstrap();
    if (!mounted) return;
    final auth = ref.read(authControllerProvider);
    if (auth.isAuthenticated) {
      final permissions = effectivePermissions(auth.user);
      context.go(defaultRouteForPermissions(permissions));
    } else {
      context.go(AppRoutes.login);
    }
  }

  @override
  Widget build(BuildContext context) {
    final apiUrl = ref.watch(appConfigProvider).apiBaseUrl;

    return Scaffold(
      body: Container(
        width: double.infinity,
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [AppColors.brandNavy, AppColors.brandNavyLight],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
        ),
        child: SafeArea(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const WebstudioLogo(height: 56, forDarkBackground: true),
              const SizedBox(height: AppSpacing.xxl),
              const CircularProgressIndicator(color: Colors.white),
              const SizedBox(height: AppSpacing.lg),
              Text(
                _status,
                style: const TextStyle(color: Colors.white70, fontSize: 14),
                textAlign: TextAlign.center,
              ),
              if (apiUrl.isNotEmpty) ...[
                const SizedBox(height: AppSpacing.md),
                Text(
                  apiUrl,
                  style: const TextStyle(color: Colors.white38, fontSize: 11),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
