import 'package:flutter_test/flutter_test.dart';
import 'package:webstudio_ims/features/inventory/domain/inventory_models.dart';
import 'package:webstudio_ims/features/inventory/domain/product_category.dart';
import 'package:webstudio_ims/features/inventory/domain/stock_model_card_utils.dart';

void main() {
  test('splitModelNotes separates marketing description from spec lines', () {
    const notes = 'DESCRIPTION:\nGreat gaming laptop\n\nProcessor: Ryzen 7\nBattery: 90Wh';
    final split = splitModelNotes(notes);
    expect(split.description, 'Great gaming laptop');
    expect(split.specNotes, contains('Processor: Ryzen 7'));
  });

  test('displayModelTitle removes duplicate brand prefix', () {
    expect(
      displayModelTitle('ASUS', 'ASUS ROG Zephyrus G14'),
      'ROG Zephyrus G14',
    );
    expect(displayModelTitle('HP', 'EliteBook 840'), 'EliteBook 840');
    expect(displayModelTitle('', 'Vivobook 15'), 'Vivobook 15');
  });

  test('buildStockModelSpecLines includes defaults and note extras', () {
    const model = ProductModel(
      id: 'm1',
      brandId: 1,
      modelNumber: 'X515',
      modelName: 'Vivobook 15',
      cpu: 'Intel Core i5',
      ramGb: 16,
      storageValue: '512',
      storageUnit: 'GB',
      storageType: 'SSD',
      status: 'active',
      notes: 'OS: Windows 11 Home',
    );

    final lines = orderStockCardSpecLines(buildStockModelSpecLines(model));
    expect(lines.any((line) => line.label == 'Processor' && line.value.contains('i5')), isTrue);
    expect(lines.any((line) => line.label == 'OS' && line.value.contains('Windows')), isTrue);
  });

  test('formatCardPrice matches desktop wording', () {
    expect(formatCardPrice(null), 'Price on request');
    expect(formatCardPrice(87000), '₹ 87000.00');
  });

  test('displayScreenHint extracts inch size', () {
    expect(displayScreenHintFromText('15.6 inch FHD'), '15.6"');
  });

  test('formatLivePrice shows NA rather than "Price on request"', () {
    expect(formatLivePrice(null), 'NA');
    expect(formatLivePrice(0), 'NA');
    expect(formatLivePrice(81990), '₹ 81990.00');
  });

  test('formatRelativeTime buckets recent timestamps into coarse labels', () {
    final now = DateTime(2026, 9, 12, 12, 0, 0);
    expect(formatRelativeTime(now.subtract(const Duration(seconds: 30)), now: now), 'just now');
    expect(formatRelativeTime(now.subtract(const Duration(minutes: 5)), now: now), '5 mins ago');
    expect(formatRelativeTime(now.subtract(const Duration(hours: 2)), now: now), '2 hours ago');
    expect(formatRelativeTime(now.subtract(const Duration(days: 3)), now: now), '3 days ago');
  });

  test('ProductModel.isAsusBrand matches brand name case-insensitively', () {
    const asus = ProductModel(
      id: 'm2',
      brandId: 2,
      brandName: ' asus ',
      modelNumber: 'M1605NAQ-MB095WS',
      modelName: 'Vivobook 16',
      status: 'active',
    );
    const other = ProductModel(
      id: 'm3',
      brandId: 3,
      brandName: 'HP',
      modelNumber: 'X360',
      modelName: 'Pavilion',
      status: 'active',
    );
    expect(asus.isAsusBrand, isTrue);
    expect(other.isAsusBrand, isFalse);
  });

  test('ProductModel.isAsusLaptop excludes ASUS accessories', () {
    const asusLaptop = ProductModel(
      id: 'm5',
      brandId: 2,
      brandName: 'ASUS',
      modelNumber: 'M1605NAQ-MB095WS',
      modelName: 'Vivobook 16',
      status: 'active',
    );
    const asusAccessory = ProductModel(
      id: 'm6',
      brandId: 2,
      brandName: 'ASUS',
      category: ProductCategory.accessory,
      modelNumber: 'AC65-06',
      modelName: '65W USB Type-C AC Adapter',
      status: 'active',
    );
    expect(asusLaptop.isAsusLaptop, isTrue);
    expect(asusAccessory.isAsusLaptop, isFalse);
  });

  test('ProductModel.fromJson parses live price fields', () {
    final model = ProductModel.fromJson(const {
      'id': 'm4',
      'brand_id': 4,
      'brand_name': 'ASUS',
      'model_number': 'FA506NCQ-IN080W',
      'model_name': 'TUF Gaming F15',
      'status': 'active',
      'live_price': 92990.0,
      'live_price_status': 'ok',
      'live_price_source_url': 'https://in.store.asus.com/example.html',
      'live_price_checked_at': '2026-09-10T10:00:00Z',
      'live_price_updated_at': '2026-09-10T10:00:00Z',
    });
    expect(model.livePrice, 92990.0);
    expect(model.livePriceStatus, 'ok');
    expect(model.livePriceSourceUrl, 'https://in.store.asus.com/example.html');
    expect(model.livePriceUpdatedAt, isNotNull);
  });
}
