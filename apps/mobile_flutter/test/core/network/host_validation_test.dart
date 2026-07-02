import 'package:flutter_test/flutter_test.dart';
import 'package:webstudio_ims/core/network/host_validation.dart';

void main() {
  test('normalizeServerHost accepts IPv4', () {
    expect(normalizeServerHost('192.168.1.10'), '192.168.1.10');
  });

  test('normalizeServerHost accepts hostname', () {
    expect(normalizeServerHost('WEBSTUDIO-SERVER'), 'webstudio-server');
  });

  test('normalizeServerHost accepts mDNS local', () {
    expect(normalizeServerHost('WEBSTUDIO-SERVER.local'), 'webstudio-server.local');
  });

  test('normalizeServerUrl adds scheme and port', () {
    expect(normalizeServerUrl('192.168.1.10'), 'http://192.168.1.10:8000');
    expect(normalizeServerUrl('WEBSTUDIO-SERVER.local:9000'), 'http://webstudio-server.local:9000');
  });

  test('normalizeServerHost rejects invalid input', () {
    expect(() => normalizeServerHost('bad host!'), throwsA(isA<HostValidationException>()));
  });
}
