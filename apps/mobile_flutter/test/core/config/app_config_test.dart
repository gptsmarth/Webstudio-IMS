import 'package:flutter_test/flutter_test.dart';
import 'package:webstudio_ims/core/config/app_config.dart';

void main() {
  test('discoveryCandidates matches desktop defaults', () {
    expect(AppConfig.discoveryCandidates(), contains('http://127.0.0.1:8000'));
    expect(AppConfig.discoveryCandidates(), contains('http://192.168.1.100:8000'));
    expect(AppConfig.discoveryCandidates(), contains('http://192.168.1.1:8000'));
  });
}
