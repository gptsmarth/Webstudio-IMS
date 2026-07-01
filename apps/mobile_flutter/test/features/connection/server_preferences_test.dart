import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:webstudio_ims/features/connection/data/server_preferences.dart';
import 'package:webstudio_ims/features/connection/domain/server_models.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('ServerPreferences', () {
    late SharedPreferences prefs;

    setUp(() async {
      SharedPreferences.setMockInitialValues({});
      prefs = await SharedPreferences.getInstance();
    });

    test('persists saved servers with recency ordering', () async {
      final storage = ServerPreferences(prefs);
      await storage.saveServer(const SavedServer(url: 'http://192.168.1.10:8000', label: 'LAN'));
      await storage.saveServer(const SavedServer(url: 'http://10.0.2.2:8000', label: 'Emulator'));

      final servers = storage.listSavedServers();
      expect(servers, hasLength(2));
      expect(servers.first.url, 'http://10.0.2.2:8000');
    });

    test('remember me stores username only', () async {
      final storage = ServerPreferences(prefs);
      await storage.setRememberMe(enabled: true, username: 'admin');
      expect(storage.getRememberMe(), isTrue);
      expect(storage.getSavedUsername(), 'admin');

      await storage.setRememberMe(enabled: false);
      expect(storage.getRememberMe(), isFalse);
      expect(storage.getSavedUsername(), isNull);
    });
  });
}
