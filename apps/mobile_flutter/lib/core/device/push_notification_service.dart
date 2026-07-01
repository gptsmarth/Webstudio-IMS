import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Push notification architecture. Remote FCM/APNs wiring is deferred;
/// local notifications provide background alert plumbing for in-app events.
abstract class PushNotificationService {
  Future<void> initialize();
  Future<bool> requestPermission();
  Future<void> showLocalAlert({
    required int id,
    required String title,
    required String body,
  });
  Future<void> cancel(int id);
}

class LocalPushNotificationService implements PushNotificationService {
  LocalPushNotificationService() : _plugin = FlutterLocalNotificationsPlugin();

  final FlutterLocalNotificationsPlugin _plugin;
  bool _initialized = false;

  static const _channelId = 'webstudio_ims_alerts';
  static const _channelName = 'WEBSTUDIO IMS Alerts';

  @override
  Future<void> initialize() async {
    if (_initialized) return;
    const android = AndroidInitializationSettings('@mipmap/ic_launcher');
    const ios = DarwinInitializationSettings();
    await _plugin.initialize(
      const InitializationSettings(android: android, iOS: ios),
      onDidReceiveNotificationResponse: _onNotificationTap,
    );
    await _plugin
        .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(
          const AndroidNotificationChannel(
            _channelId,
            _channelName,
            description: 'Operational alerts from WEBSTUDIO IMS',
            importance: Importance.high,
          ),
        );
    _initialized = true;
  }

  @override
  Future<bool> requestPermission() async {
    if (defaultTargetPlatform == TargetPlatform.iOS) {
      final ios = _plugin.resolvePlatformSpecificImplementation<IOSFlutterLocalNotificationsPlugin>();
      final granted = await ios?.requestPermissions(alert: true, badge: true, sound: true);
      return granted ?? false;
    }
    final android = _plugin.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();
    final granted = await android?.requestNotificationsPermission();
    return granted ?? true;
  }

  @override
  Future<void> showLocalAlert({
    required int id,
    required String title,
    required String body,
  }) async {
    await initialize();
    const details = NotificationDetails(
      android: AndroidNotificationDetails(
        _channelId,
        _channelName,
        importance: Importance.high,
        priority: Priority.high,
      ),
      iOS: DarwinNotificationDetails(),
    );
    await _plugin.show(id, title, body, details);
  }

  @override
  Future<void> cancel(int id) => _plugin.cancel(id);

  void _onNotificationTap(NotificationResponse response) {
    // Deep-link routing will be attached when remote push payloads are introduced.
  }
}

/// Coordinates foreground refresh with local notification surfacing.
class BackgroundNotificationCoordinator {
  const BackgroundNotificationCoordinator(this._push);

  final PushNotificationService _push;

  Future<void> notifyNewAlerts({
    required int unreadCount,
    required String latestTitle,
  }) async {
    if (unreadCount <= 0) return;
    await _push.showLocalAlert(
      id: 1001,
      title: 'WEBSTUDIO IMS',
      body: unreadCount == 1 ? latestTitle : '$unreadCount new notifications',
    );
  }
}

final pushNotificationServiceProvider = Provider<PushNotificationService>(
  (ref) => LocalPushNotificationService(),
);

final backgroundNotificationCoordinatorProvider = Provider<BackgroundNotificationCoordinator>(
  (ref) => BackgroundNotificationCoordinator(ref.watch(pushNotificationServiceProvider)),
);
