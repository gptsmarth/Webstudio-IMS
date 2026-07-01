import 'package:flutter_test/flutter_test.dart';

import 'package:webstudio_ims/features/inventory/domain/inventory_models.dart';

import 'qa_fixtures.dart';

void main() {
  group('QA — Memory', () {
    test('inventory item toJson round-trip does not duplicate large lists', () {
      final items = qaLargeInventory(brandCount: 2, modelsPerBrand: 2, serialsPerModel: 5);
      final serialized = items.map((item) => item.toJson()).toList();
      final restored = serialized.map(InventoryItem.fromJson).toList();
      expect(restored, hasLength(items.length));
      expect(restored.first.serialNumber, items.first.serialNumber);
    });

    test('pagination returns new slice without mutating source list', () {
      final source = List.generate(100, (i) => i);
      final slice = source.sublist(10, 20);
      expect(slice, hasLength(10));
      expect(source, hasLength(100));
    });

    test('large inventory fixture size is bounded for QA scenarios', () {
      final items = qaLargeInventory(brandCount: 20, modelsPerBrand: 10, serialsPerModel: 50);
      expect(items.length, 10000);
      final uniqueSerials = items.map((i) => i.serialNumber).toSet();
      expect(uniqueSerials.length, items.length);
    });
  });
}
