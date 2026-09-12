import 'package:shared_preferences/shared_preferences.dart';

const _stockShowSellingPriceKey = 'webstudio_stock_show_selling_price';
const _stockShowLivePriceKey = 'webstudio_stock_show_live_price';

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
}
