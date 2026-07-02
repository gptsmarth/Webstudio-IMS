import 'package:flutter_test/flutter_test.dart';
import 'package:webstudio_ims/features/connection/domain/server_models.dart';

void main() {
  test('SavedServer round-trips extended metadata', () {
    const server = SavedServer(
      url: 'http://webstudio-server.local:8000',
      friendlyName: 'Acme Retail',
      companyName: 'Acme Retail',
      hostname: 'webstudio-server.local',
      currentIp: '192.168.1.10',
      backendVersion: '0.1.0',
    );
    final decoded = SavedServer.fromJson(server.toJson());
    expect(decoded.url, server.url);
    expect(decoded.hostname, server.hostname);
    expect(decoded.currentIp, server.currentIp);
    expect(decoded.backendVersion, server.backendVersion);
    expect(decoded.displayLabel, 'Acme Retail');
  });

  test('SavedServer backward compatible with legacy json', () {
    final decoded = SavedServer.fromJson({
      'url': 'http://127.0.0.1:8000',
      'label': 'WEBSTUDIO',
      'last_connected_at': '2026-01-01T00:00:00.000Z',
    });
    expect(decoded.url, 'http://127.0.0.1:8000');
    expect(decoded.label, 'WEBSTUDIO');
    expect(decoded.lastConnectedAt, isNotNull);
  });
}
