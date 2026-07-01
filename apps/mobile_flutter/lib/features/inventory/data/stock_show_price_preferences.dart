import 'package:shared_preferences/shared_preferences.dart';

const _stockShowSellingPriceKey = 'webstudio_stock_show_selling_price';

/// Mirrors desktop `useStockNavStore` localStorage preference (default: show prices).
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
}
