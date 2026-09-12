import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/config/app_config_provider.dart';
import '../../../core/routing/app_routes.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/theme_mode_provider.dart';
import '../../../shared/widgets/webstudio_logo.dart';
import '../../../core/version/version_check_controller.dart';
import 'auth_controller.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  final _usernameFocus = FocusNode();
  bool _rememberMe = true;
  bool _obscurePassword = true;
  bool _submitting = false;
  Timer? _lockoutTimer;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final saved = ref.read(authControllerProvider.notifier).savedUsername();
      final remember = ref.read(authControllerProvider.notifier).rememberMeDefault;
      if (saved != null) {
        _usernameController.text = saved;
        _rememberMe = remember;
      }
      _usernameFocus.requestFocus();
      _startLockoutTimer();
    });
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final expired = ref.read(authControllerProvider);
    if (expired.status == AuthStatus.sessionExpired && expired.errorMessage != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(expired.errorMessage!)),
        );
      });
    }
  }

  @override
  void dispose() {
    _lockoutTimer?.cancel();
    _usernameController.dispose();
    _passwordController.dispose();
    _usernameFocus.dispose();
    super.dispose();
  }

  void _startLockoutTimer() {
    _lockoutTimer?.cancel();
    _lockoutTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      final auth = ref.read(authControllerProvider);
      if (auth.isLockedOut) {
        if (mounted) setState(() {});
      } else {
        ref.read(authControllerProvider.notifier).clearLockoutIfExpired();
        _lockoutTimer?.cancel();
      }
    });
  }

  Future<void> _submit() async {
    if (ref.read(authControllerProvider).isLockedOut) return;
    if (!_formKey.currentState!.validate()) return;
    setState(() => _submitting = true);
    final ok = await ref.read(authControllerProvider.notifier).login(
          username: _usernameController.text.trim(),
          password: _passwordController.text,
          rememberMe: _rememberMe,
        );
    if (!mounted) return;
    setState(() => _submitting = false);
    if (ok) {
      await ref.read(versionCheckControllerProvider.notifier).check(
            trigger: VersionCheckTrigger.login,
            context: context,
          );
      if (!mounted) return;
      if (ref.read(versionCheckControllerProvider).mandatoryBlocked) return;
      await Future<void>.delayed(const Duration(milliseconds: 400));
      if (mounted) context.go(AppRoutes.dashboard);
    } else {
      _startLockoutTimer();
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authControllerProvider);
    final apiUrl = ref.watch(appConfigProvider).apiBaseUrl;
    final themeMode = ref.watch(themeModeProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Sign in'),
        actions: [
          IconButton(
            tooltip: 'Toggle theme',
            onPressed: () {
              final next = switch (themeMode) {
                ThemeMode.dark => AppThemeMode.light,
                ThemeMode.light => AppThemeMode.dark,
                ThemeMode.system => isDark ? AppThemeMode.light : AppThemeMode.dark,
              };
              ref.read(themeModeProvider.notifier).setMode(next);
            },
            icon: Icon(isDark ? Icons.light_mode_outlined : Icons.dark_mode_outlined),
          ),
        ],
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(AppSpacing.xl),
          children: [
            _BrandHeader(),
            const SizedBox(height: AppSpacing.xl),
            if (apiUrl.isNotEmpty)
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.dns_outlined, size: 20),
                title: Text(apiUrl, style: Theme.of(context).textTheme.bodySmall),
                subtitle: const Text('Connected server'),
                trailing: TextButton(
                  onPressed: _submitting ? null : () => context.push(AppRoutes.connection),
                  child: const Text('Change'),
                ),
              ),
            const SizedBox(height: AppSpacing.lg),
            Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  TextFormField(
                    controller: _usernameController,
                    focusNode: _usernameFocus,
                    decoration: const InputDecoration(labelText: 'Username'),
                    textInputAction: TextInputAction.next,
                    autofillHints: const [AutofillHints.username],
                    enabled: !_submitting && !auth.isLockedOut,
                    validator: (v) => (v == null || v.trim().isEmpty) ? 'Username is required' : null,
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  TextFormField(
                    controller: _passwordController,
                    decoration: InputDecoration(
                      labelText: 'Password',
                      suffixIcon: IconButton(
                        icon: Icon(_obscurePassword ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                        onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                      ),
                    ),
                    obscureText: _obscurePassword,
                    textInputAction: TextInputAction.done,
                    autofillHints: const [AutofillHints.password],
                    enabled: !_submitting && !auth.isLockedOut,
                    onFieldSubmitted: (_) => _submit(),
                    validator: (v) => (v == null || v.isEmpty) ? 'Password is required' : null,
                  ),
                  const SizedBox(height: AppSpacing.md),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Remember me'),
                    subtitle: const Text('Saves username only — never your password'),
                    value: _rememberMe,
                    onChanged: _submitting ? null : (v) => setState(() => _rememberMe = v),
                  ),
                  if (auth.statusMessage != null && _submitting) ...[
                    const SizedBox(height: AppSpacing.md),
                    Row(
                      children: [
                        const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        ),
                        const SizedBox(width: AppSpacing.sm),
                        Expanded(child: Text(auth.statusMessage!, style: Theme.of(context).textTheme.bodySmall)),
                      ],
                    ),
                  ],
                  if (auth.errorMessage != null) ...[
                    const SizedBox(height: AppSpacing.md),
                    _ErrorBanner(message: auth.errorMessage!),
                  ],
                  if (auth.isLockedOut) ...[
                    const SizedBox(height: AppSpacing.sm),
                    Text(
                      'Try again in ${auth.lockoutSecondsRemaining}s',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                  const SizedBox(height: AppSpacing.xl),
                  ElevatedButton(
                    onPressed: _submitting || auth.isLockedOut ? null : _submit,
                    child: _submitting
                        ? const SizedBox(
                            height: 20,
                            width: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text('Sign in'),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _BrandHeader extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.xxl),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF0088CC), Color(0xFF005580)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(AppSpacing.radiusXl),
      ),
      child: const Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Center(child: WebstudioLogo(height: 44, forDarkBackground: true)),
          SizedBox(height: AppSpacing.lg),
          Text(
            'A Multi-Brand Computer Store',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white70,
              fontSize: 12,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.2,
            ),
          ),
          SizedBox(height: AppSpacing.md),
          Text(
            'Inventory Management',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w600),
          ),
          SizedBox(height: AppSpacing.sm),
          Text(
            'Sign in with your WEBSTUDIO account',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.white70, fontSize: 14),
          ),
          SizedBox(height: AppSpacing.lg),
          Text(
            '22, D.A.V. Market, Opp. Madhu Hotel, Yamunanagar',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.white70, fontSize: 12, height: 1.4),
          ),
          SizedBox(height: 4),
          Text(
            '26-29 F, D.A.V. Market, Yamunanagar',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.white70, fontSize: 12, height: 1.4),
          ),
          SizedBox(height: AppSpacing.lg),
          Text(
            'POWERED BY TECHSS',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white38,
              fontSize: 10,
              fontWeight: FontWeight.w600,
              letterSpacing: 1.2,
            ),
          ),
        ],
      ),
    );
  }
}

class _ErrorBanner extends StatelessWidget {
  const _ErrorBanner({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Theme.of(context).colorScheme.errorContainer,
      borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.error_outline, color: Theme.of(context).colorScheme.error, size: 18),
            const SizedBox(width: AppSpacing.sm),
            Expanded(child: Text(message)),
          ],
        ),
      ),
    );
  }
}
