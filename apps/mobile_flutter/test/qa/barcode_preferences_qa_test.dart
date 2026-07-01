import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:webstudio_ims/features/inventory/data/barcode_scan_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('BarcodeScanPreferences', () {
    setUp(() async {
      SharedPreferences.setMockInitialValues({});
    });

    test('defaults sound and haptic to enabled', () async {
      expect(await BarcodeScanPreferences.soundEnabled(), isTrue);
      expect(await BarcodeScanPreferences.hapticEnabled(), isTrue);
    });

    test('persists toggles', () async {
      await BarcodeScanPreferences.setSoundEnabled(false);
      await BarcodeScanPreferences.setHapticEnabled(false);
      expect(await BarcodeScanPreferences.soundEnabled(), isFalse);
      expect(await BarcodeScanPreferences.hapticEnabled(), isFalse);
    });
  });
}
