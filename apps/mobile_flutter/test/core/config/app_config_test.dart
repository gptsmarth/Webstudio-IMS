import 'package:flutter_test/flutter_test.dart';
import 'package:webstudio_ims/core/config/app_config.dart';

void main() {
  test('discoveryCandidates prioritizes shop LAN server before localhost', () {
    final candidates = AppConfig.discoveryCandidates();
    expect(candidates.first, 'http://192.168.29.100:8000');
    expect(candidates, contains('http://192.168.1.100:8000'));
  });

  test('shouldOpenConnectionSetupFirst rejects empty and emulator URLs on release paths', () {
    expect(AppConfig.shouldOpenConnectionSetupFirst(''), isTrue);
    expect(AppConfig.isEmulatorLoopbackUrl('http://10.0.2.2:8000'), isTrue);
  });
}
