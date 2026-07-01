import 'package:shared_preferences/shared_preferences.dart';

/// Device-local barcode scanner UX preferences (sound / haptic).
class BarcodeScanPreferences {
  static const _soundKey = 'webstudio_barcode_sound';
  static const _hapticKey = 'webstudio_barcode_haptic';

  static Future<bool> soundEnabled() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_soundKey) ?? true;
  }

  static Future<bool> hapticEnabled() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_hapticKey) ?? true;
  }

  static Future<void> setSoundEnabled(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_soundKey, value);
  }

  static Future<void> setHapticEnabled(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_hapticKey, value);
  }
}
