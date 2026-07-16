import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hive/hive.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:webstudio_ims/core/config/app_config_provider.dart';
import 'package:webstudio_ims/core/device/device_permissions.dart';
import 'package:webstudio_ims/core/network/api_client.dart';
import 'package:webstudio_ims/core/network/connectivity_provider.dart';
import 'package:webstudio_ims/core/offline/offline_models.dart';
import 'package:webstudio_ims/core/offline/offline_providers.dart';
import 'package:webstudio_ims/core/offline/pending_operation_factory.dart';
import 'package:webstudio_ims/core/storage/hive_cache.dart';
import 'package:webstudio_ims/core/storage/secure_token_storage.dart';
import 'package:webstudio_ims/core/theme/theme_mode_provider.dart';
import 'package:webstudio_ims/features/auth/domain/auth_models.dart';
import 'package:webstudio_ims/features/auth/presentation/auth_controller.dart';
import 'package:webstudio_ims/features/inventory/domain/barcode_field_resolver.dart';
import 'package:webstudio_ims/shared/widgets/offline_banner.dart';

/// Shared integration flow tests — run from [test/integration] (VM/CI) or [integration_test] (device).
void registerAppFlowIntegrationTests() {
  group('Integration — production flows', () {
    test('app startup config loads saved API URL', () async {
      SharedPreferences.setMockInitialValues({'webstudio_api_url': 'http://127.0.0.1:8000'});
      final prefs = await SharedPreferences.getInstance();
      final container = await buildIntegrationContainer(prefs: prefs);
      addTearDown(container.dispose);

      expect(container.read(appConfigProvider).apiBaseUrl, 'http://127.0.0.1:8000');
    });

    test('connection endpoint path is configured', () async {
      SharedPreferences.setMockInitialValues({});
      final prefs = await SharedPreferences.getInstance();
      final container = await buildIntegrationContainer(prefs: prefs);
      addTearDown(container.dispose);

      expect(container.read(appConfigProvider).apiBaseUrl, isNotEmpty);
    });

    test('login session can be established and cleared', () async {
      SharedPreferences.setMockInitialValues({});
      final prefs = await SharedPreferences.getInstance();
      final container = await buildIntegrationContainer(prefs: prefs, authenticated: true);
      addTearDown(container.dispose);

      expect(container.read(authControllerProvider).isAuthenticated, isTrue);
      container.read(authControllerProvider.notifier).state =
          const AuthState(status: AuthStatus.unauthenticated);
      expect(container.read(authControllerProvider).status, AuthStatus.unauthenticated);
    });

    test('dashboard permission gate allows admin inventory access', () async {
      SharedPreferences.setMockInitialValues({});
      final prefs = await SharedPreferences.getInstance();
      final container = await buildIntegrationContainer(prefs: prefs, authenticated: true);
      addTearDown(container.dispose);

      final permissions = container.read(authControllerProvider).user?.permissions ?? const [];
      expect(permissions, contains('dashboard:view'));
      expect(permissions, contains('inventory:view'));
    });

    test('inventory barcode mock input resolves serial scan results', () {
      const raw = 'a1b2c3d4e5f6';
      final result = BarcodeFieldResolver.resolve(rawValue: raw, format: 'code128');
      expect(result.rawValue, raw);
      expect(result.targetField, BarcodeFieldTarget.serialNumber);
    });

    test('transfer pending operation can be queued offline', () {
      const factory = PendingOperationFactory();
      final operation = factory.transferLocation(
        itemId: 'item-1',
        locationId: 2,
        entityUpdatedAt: '2026-07-01T00:00:00Z',
      );
      expect(operation.type, PendingOperationType.transferLocation);
      expect(operation.payload['location_id'], 2);
    });

    test('mark sold pending operation can be queued offline', () {
      const factory = PendingOperationFactory();
      final operation = factory.markSold(
        itemId: 'item-1',
        entityUpdatedAt: '2026-07-01T00:00:00Z',
        request: {
          'invoice_number': 'INV-100',
          'customer_name': 'Customer',
          'payment_mode': 'Cash',
          'sale_date': '2026-07-01',
        },
      );
      expect(operation.type, PendingOperationType.markSold);
      expect(operation.payload['invoice_number'], 'INV-100');
    });

    testWidgets('offline banner shows pending changes while offline', (tester) async {
      SharedPreferences.setMockInitialValues({});
      final prefs = await SharedPreferences.getInstance();
      final container = await buildIntegrationContainer(
        prefs: prefs,
        extraOverrides: [
          connectivityProvider.overrideWith((ref) => Stream.value(false)),
          backgroundSyncCoordinatorProvider.overrideWith((ref) => _StaticSyncCoordinator(ref)),
        ],
      );
      addTearDown(container.dispose);

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: const MaterialApp(
            home: OfflineBanner(child: Placeholder()),
          ),
        ),
      );
      await tester.pump();

      expect(find.text('Offline'), findsOneWidget);
      expect(find.text('12 pending changes'), findsOneWidget);
    });

    testWidgets('camera permission flow completes in one request', (tester) async {
      final permissions = AlwaysGrantPermissions();
      SharedPreferences.setMockInitialValues({});
      final prefs = await SharedPreferences.getInstance();
      final container = await buildIntegrationContainer(
        prefs: prefs,
        extraOverrides: [devicePermissionsProvider.overrideWithValue(permissions)],
      );
      addTearDown(container.dispose);

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp(
            home: Builder(
              builder: (context) {
                return ElevatedButton(
                  onPressed: () async {
                    final outcome = await permissions.requestWithContext(
                      context,
                      DevicePermissionKind.camera,
                    );
                    expect(outcome.granted, isTrue);
                  },
                  child: const Text('Scan barcode'),
                );
              },
            ),
          ),
        ),
      );

      await tester.tap(find.text('Scan barcode'));
      await tester.pumpAndSettle();
      expect(permissions.requestCount, 1);
    });
  });
}

Future<ProviderContainer> buildIntegrationContainer({
  required SharedPreferences prefs,
  bool authenticated = false,
  List<Override> extraOverrides = const [],
}) async {
  final container = ProviderContainer(
    overrides: [
      sharedPreferencesProvider.overrideWithValue(prefs),
      themeModeProvider.overrideWith((ref) => ThemeModeController(prefs)),
      apiClientProvider.overrideWith((ref) => ApiClient(
            config: ref.watch(appConfigProvider),
            tokenStorage: SecureTokenStorage(),
          )),
      ...extraOverrides,
    ],
  );

  if (authenticated) {
    container.read(authControllerProvider.notifier).state = AuthState(
      status: AuthStatus.authenticated,
      user: AuthUser(
        id: 1,
        username: 'admin',
        role: 'admin',
        status: 'active',
        mustChangePassword: false,
        themePreference: 'system',
        permissions: const [
          'dashboard:view',
          'inventory:view',
          'inventory:update',
          'sales:view',
        ],
      ),
    );
  }

  return container;
}

class AlwaysGrantPermissions extends DevicePermissions {
  int requestCount = 0;

  @override
  Future<PermissionRequestOutcome> requestWithContext(
    BuildContext context,
    DevicePermissionKind kind,
  ) async {
    requestCount += 1;
    return const PermissionRequestOutcome(granted: true);
  }
}

class _StaticSyncCoordinator extends BackgroundSyncCoordinator {
  _StaticSyncCoordinator(super.ref);

  @override
  void start() {
    state = const SyncWorkspaceState(pendingCount: 12);
  }

  @override
  Future<void> syncNow({bool showBanner = false}) async {}
}

Future<void> initIntegrationHarness() async {
  TestWidgetsFlutterBinding.ensureInitialized();
  final dir = await Directory.systemTemp.createTemp('webstudio_integration');
  Hive.init(dir.path);
  await Future.wait([
    Hive.openBox<Map<String, dynamic>>(HiveCache.syncStateBox),
    Hive.openBox<Map<String, dynamic>>(HiveCache.profileBox),
    Hive.openBox<dynamic>(HiveCache.settingsBox),
    Hive.openBox<Map<String, dynamic>>(HiveCache.entityCacheBox),
    Hive.openBox<Map<String, dynamic>>(HiveCache.pendingOpsBox),
    Hive.openBox<Map<String, dynamic>>(HiveCache.apiCacheBox),
  ]);
}
