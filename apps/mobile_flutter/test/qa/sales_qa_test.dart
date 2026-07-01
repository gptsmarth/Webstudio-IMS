import 'package:flutter_test/flutter_test.dart';

import 'package:webstudio_ims/features/catalogue/domain/catalogue_models.dart';
import 'package:webstudio_ims/features/sales/domain/sales_models.dart';

void main() {
  group('QA — Sales', () {
    test('SaleDetail parses desktop parity fields', () {
      final detail = SaleDetail.fromJson({
        'id': 42,
        'inventory_item_id': 'item-1',
        'serial_number': 'SN-001',
        'brand_id': 1,
        'brand_name': 'Dell',
        'product_model_id': 'model-1',
        'model_number': 'XPS-15',
        'model_name': 'XPS 15',
        'location_id': 1,
        'location_name': 'Floor',
        'color': 'Black',
        'cpu': 'i7',
        'ram_gb': 16,
        'storage_value': '512',
        'storage_unit': 'GB',
        'storage_type': 'SSD',
        'invoice_number': 'INV-42',
        'customer_name': 'Acme Corp',
        'payment_mode': 'UPI',
        'sale_amount': 150000.0,
        'sale_source': 'manual',
        'sold_at': '2026-06-01T10:00:00Z',
        'created_at': '2026-06-01T10:00:00Z',
      });
      expect(detail.invoiceNumber, 'INV-42');
      expect(detail.serialNumber, 'SN-001');
      expect(detail.saleAmount, 150000.0);
    });

    test('SalesListFilters maps sort and date range', () {
      const filters = SalesListFilters(
        invoiceNumber: 'INV',
        customerName: 'Acme',
        paymentMode: 'Cash',
        dateFrom: '2026-01-01',
        dateTo: '2026-06-30',
      );
      final params = filters.toQueryParams(
        page: 2,
        pageSize: 25,
        search: 'INV',
        sortField: SalesSortField.soldAt,
        sortDirection: 'desc',
      );
      expect(params['search'], 'INV');
      expect(params['payment_mode'], 'Cash');
      expect(params['sort_field'], 'sold_at');
      expect(params['sort_direction'], 'desc');
      expect(params['page'], 2);
    });

    test('catalogue pagination slices large result sets', () {
      final items = List.generate(250, (i) => 'item-$i');
      final page1 = paginateItems(items, 1, 50);
      final page5 = paginateItems(items, 5, 50);
      expect(page1, hasLength(50));
      expect(page5, hasLength(50));
      expect(page5.first, 'item-200');
    });
  });
}
