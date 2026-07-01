import 'package:flutter_test/flutter_test.dart';

import 'package:webstudio_ims/features/catalogue/domain/catalogue_models.dart';
import 'package:webstudio_ims/features/sales/domain/sales_models.dart';

void main() {
  group('catalogue pagination', () {
    test('paginateItems returns correct slice', () {
      final items = List.generate(30, (i) => i);
      expect(paginateItems(items, 1, 25), hasLength(25));
      expect(paginateItems(items, 2, 25), hasLength(5));
    });
  });

  group('SalesListFilters', () {
    test('toQueryParams maps filters and sort', () {
      const filters = SalesListFilters(
        brandId: 2,
        locationId: 3,
        paymentMode: 'Cash',
        dateFrom: '2026-01-01',
      );
      final params = filters.toQueryParams(
        page: 2,
        pageSize: 50,
        search: 'INV-1',
        sortField: SalesSortField.soldAt,
        sortDirection: 'desc',
      );
      expect(params['page'], 2);
      expect(params['brand_id'], 2);
      expect(params['search'], 'INV-1');
      expect(params['sort_field'], 'sold_at');
      expect(params['date_from'], '2026-01-01T00:00:00Z');
    });
  });
}
