import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'core/config/app_config_provider.dart';
import 'core/device/push_notification_service.dart';
import 'core/network/api_client.dart';
import 'core/storage/hive_cache.dart';
import 'core/storage/secure_token_storage.dart';
import 'core/theme/theme_mode_provider.dart';
import 'features/auth/presentation/auth_controller.dart';

class AppBootstrap {
  static Future<ProviderContainer> createContainer() async {
    WidgetsFlutterBinding.ensureInitialized();
    await HiveCache.init();
    final prefs = await SharedPreferences.getInstance();
    final tokenStorage = SecureTokenStorage();

    final container = ProviderContainer(
      overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
        themeModeProvider.overrideWith((ref) => ThemeModeController(prefs)),
        apiClientProvider.overrideWith((ref) {
          final appConfig = ref.watch(appConfigProvider);
          final client = ApiClient(
            config: appConfig,
            tokenStorage: tokenStorage,
            onRefreshToken: () => ref.read(authControllerProvider.notifier).refreshTokens(),
          );
          ref.listen(appConfigProvider, (previous, next) {
            if (previous?.apiBaseUrl != next.apiBaseUrl ||
                previous?.clientVersion != next.clientVersion ||
                previous?.clientPlatform != next.clientPlatform) {
              client.updateConfig(next);
            }
          });
          return client;
        }),
      ],
    );

    container.read(appConfigProvider.notifier);
    await container.read(pushNotificationServiceProvider).initialize();
    return container;
  }
}
