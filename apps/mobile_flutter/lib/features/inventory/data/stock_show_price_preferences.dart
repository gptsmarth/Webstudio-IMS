import 'package:shared_preferences/shared_preferences.dart';

const _stockShowSellingPriceKey = 'webstudio_stock_show_selling_price';
const _stockShowLivePriceKey = 'webstudio_stock_show_live_price';
const _asusPriceRunDismissedAtKey = 'webstudio_asus_price_run_dismissed_at';

/// Mirrors desktop `useHierarchyNavStore` localStorage preferences (default: show prices).
class StockShowPricePreferences {
  static Future<bool> readShowSellingPrice() async {
    final prefs = await SharedPreferences.getInstance();
    final stored = prefs.getBool(_stockShowSellingPriceKey);
    if (stored == null) return true;
    return stored;
  }

  static Future<void> writeShowSellingPrice(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_stockShowSellingPriceKey, value);
  }

  static Future<bool> readShowLivePrice() async {
    final prefs = await SharedPreferences.getInstance();
    final stored = prefs.getBool(_stockShowLivePriceKey);
    if (stored == null) return true;
    return stored;
  }

  static Future<void> writeShowLivePrice(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_stockShowLivePriceKey, value);
  }

  /// The `finished_at` timestamp of the last bulk "Update prices" run the
  /// user has dismissed, so a completed run's banner doesn't keep reappearing
  /// every time the app is reopened once they've already acknowledged it.
  static Future<String?> readAsusPriceRunDismissedAt() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_asusPriceRunDismissedAtKey);
  }

  static Future<void> writeAsusPriceRunDismissedAt(String finishedAt) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_asusPriceRunDismissedAtKey, finishedAt);
  }
}
