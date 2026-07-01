import 'package:flutter_test/flutter_test.dart';
import 'package:webstudio_ims/features/inventory/domain/inventory_models.dart';
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
    expect(displayScreenHint('15.6 inch FHD'), '15.6"');
  });
}
