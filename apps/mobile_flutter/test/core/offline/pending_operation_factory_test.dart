import 'package:flutter_test/flutter_test.dart';

import 'package:webstudio_ims/core/offline/offline_models.dart';
import 'package:webstudio_ims/core/offline/pending_operation_factory.dart';

void main() {
  group('PendingOperationFactory', () {
    const factory = PendingOperationFactory();

    test('creates transfer operation with entity snapshot', () {
      final op = factory.transferLocation(
        itemId: 'abc',
        locationId: 3,
        entityUpdatedAt: '2026-06-01T00:00:00Z',
      );
      expect(op.type, PendingOperationType.transferLocation);
      expect(op.entityId, 'abc');
      expect(op.payload['location_id'], 3);
    });

    test('serializes and deserializes pending operations', () {
      final op = factory.markSold(
        itemId: 'abc',
        entityUpdatedAt: '2026-06-01T00:00:00Z',
        request: {
          'invoice_number': 'INV-1',
          'customer_name': 'Customer',
          'payment_mode': 'Cash',
          'sale_date': '2026-06-01',
        },
      );
      final restored = PendingOperation.fromJson(op.toJson());
      expect(restored.type, PendingOperationType.markSold);
      expect(restored.payload['invoice_number'], 'INV-1');
    });
  });
}
