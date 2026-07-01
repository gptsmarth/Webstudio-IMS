import 'package:flutter_test/flutter_test.dart';

import 'package:webstudio_ims/features/inventory/domain/inventory_hierarchy.dart';
import 'package:webstudio_ims/features/inventory/domain/inventory_models.dart';

import 'qa_fixtures.dart';

void main() {
  group('QA — Inventory', () {
    test('hierarchy search matches serial field', () {
      final item = qaItem(index: 1, brandId: 1, modelId: 'm1', locationId: 1);
      expect(matchesSerialSearch(item, 'SN-000001', HierarchySearchField.serial), isTrue);
      expect(matchesSerialSearch(item, 'SN-000001', HierarchySearchField.all), isTrue);
      expect(matchesSerialSearch(item, 'missing', HierarchySearchField.serial), isFalse);
    });

    test('inventory filters serialize to query params', () {
      const filters = InventoryListFilters(
        status: InventoryStatus.available,
        currentLocationId: 2,
        color: 'Black',
        includeArchived: true,
      );
      final params = filters.toQueryParams(page: 1, pageSize: 50);
      expect(params['status'], 'available');
      expect(params['current_location_id'], 2);
      expect(params['color'], 'Black');
      expect(params['include_archived'], isTrue);
    });

    test('mark sold request includes desktop parity fields', () {
      const request = MarkSoldRequest(
        invoiceNumber: 'INV-1',
        customerName: 'Customer',
        paymentMode: 'Cash',
        saleDate: '2026-06-01',
        saleAmount: 999.0,
        remarks: 'Walk-in',
      );
      final json = request.toJson();
      expect(json['invoice_number'], 'INV-1');
      expect(json['payment_mode'], 'Cash');
      expect(json['sale_amount'], 999.0);
    });

    test('buildBrandSummaries aggregates active brands only', () {
      final brands = [qaBrand(1), const Brand(id: 2, name: 'Archived Brand', isActive: false)];
      final items = qaLargeInventory(brandCount: 1, modelsPerBrand: 1, serialsPerModel: 3);
      final summaries = buildBrandSummaries(brands, qaDistributionForBrands(1), items);
      expect(summaries, hasLength(1));
      expect(summaries.first.brandId, 1);
      expect(summaries.first.totalUnits, greaterThan(0));
    });
  });
}
