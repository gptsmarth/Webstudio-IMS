import 'package:flutter_test/flutter_test.dart';

import 'package:webstudio_ims/features/catalogue/domain/catalogue_models.dart';
import 'package:webstudio_ims/features/inventory/domain/inventory_hierarchy.dart';

import 'qa_fixtures.dart';

void main() {
  group('QA — Performance (large dataset)', () {
    test('buildBrandSummaries handles 1000 items under 200ms', () {
      final brands = qaBrands(10);
      final items = qaLargeInventory(brandCount: 10, modelsPerBrand: 5, serialsPerModel: 20);
      expect(items, hasLength(1000));

      final stopwatch = Stopwatch()..start();
      final summaries = buildBrandSummaries(brands, qaDistributionForBrands(10), items);
      stopwatch.stop();

      expect(summaries, hasLength(10));
      expect(stopwatch.elapsedMilliseconds, lessThan(200));
    });

    test('client pagination handles 5000 catalogue rows', () {
      final rows = List.generate(5000, (i) => 'row-$i');
      final stopwatch = Stopwatch()..start();
      final page = paginateItems(rows, 100, 50);
      stopwatch.stop();
      expect(page, hasLength(50));
      expect(page.first, 'row-4950');
      expect(stopwatch.elapsedMilliseconds, lessThan(50));
    });

    test('serial search over 1000 cached items is linear and fast', () {
      final items = qaLargeInventory(brandCount: 5, modelsPerBrand: 4, serialsPerModel: 50);
      final target = items[777].serialNumber;
      final stopwatch = Stopwatch()..start();
      final found = items.where((item) => item.serialNumber == target).toList();
      stopwatch.stop();
      expect(found, hasLength(1));
      expect(stopwatch.elapsedMilliseconds, lessThan(100));
    });
  });
}
