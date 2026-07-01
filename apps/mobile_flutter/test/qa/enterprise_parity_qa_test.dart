import 'package:flutter_test/flutter_test.dart';

import 'package:webstudio_ims/features/inventory/domain/barcode_field_resolver.dart';
import 'package:webstudio_ims/features/search/domain/search_models.dart';

void main() {
  group('QA — Enterprise parity helpers', () {
    test('global search parses backend envelope results', () {
      final result = GlobalSearchResult.fromJson({
        'query': 'dell',
        'results': [
          {
            'type': 'inventory',
            'id': '1',
            'title': 'SN001',
            'subtitle': 'Dell XPS',
          },
        ],
      });
      expect(result.hits, hasLength(1));
      expect(result.hits.first.type, 'inventory');
      expect(result.hits.first.title, 'SN001');
    });

    test('supported barcode formats exclude internal QR', () {
      expect(supportedBarcodeFormats, isNot(contains('qr')));
    });
  });
}
