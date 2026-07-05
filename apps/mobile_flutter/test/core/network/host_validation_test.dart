import 'package:flutter_test/flutter_test.dart';
import 'package:webstudio_ims/core/network/host_validation.dart';

void main() {
  test('normalizeServerUrl accepts shop LAN address', () {
    expect(
      normalizeServerUrl('192.168.29.100:8000'),
      'http://192.168.29.100:8000',
    );
    expect(
      normalizeServerUrl('http://192.168.29.100:8000'),
      'http://192.168.29.100:8000',
    );
  });

  test('resolveServerHost skips DNS lookup for IPv4 literals', () async {
    final result = await resolveServerHost('192.168.29.100');
    expect(result.success, isTrue);
    expect(result.resolvedIp, '192.168.29.100');
    expect(result.configuredHost, '192.168.29.100');
  });
}
