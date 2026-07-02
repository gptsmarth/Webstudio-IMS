import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/routing/app_router.dart';
import 'core/theme/app_theme.dart';
import 'core/theme/theme_mode_provider.dart';
import 'core/version/mandatory_update_gate.dart';
import 'core/version/version_check_lifecycle.dart';

class WebstudioImsApp extends ConsumerWidget {
  const WebstudioImsApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    final themeMode = ref.watch(themeModeProvider);

    return VersionCheckLifecycleObserver(
      child: MandatoryUpdateGate(
        child: MaterialApp.router(
          title: 'WEBSTUDIO IMS',
          debugShowCheckedModeBanner: false,
          theme: AppTheme.light(),
          darkTheme: AppTheme.dark(),
          themeMode: themeMode,
          routerConfig: router,
        ),
      ),
    );
  }
}
