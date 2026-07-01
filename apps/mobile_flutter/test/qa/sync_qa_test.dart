import 'package:flutter_test/flutter_test.dart';

import 'package:webstudio_ims/core/offline/conflict_detector.dart';
import 'package:webstudio_ims/core/offline/offline_models.dart';
import 'package:webstudio_ims/core/offline/pending_operation_factory.dart';
import 'package:webstudio_ims/features/inventory/domain/inventory_models.dart';

InventoryItem _item(String updatedAt) => InventoryItem(
      id: '1',
      serialNumber: 'SN',
      productModelId: 'm',
      brandId: 1,
      brandName: 'B',
      modelNumber: 'MN',
      modelName: 'M',
      cpu: 'i5',
      ramGb: 8,
      storageValue: '256',
      storageUnit: 'GB',
      storageType: 'SSD',
      color: 'Black',
      currentLocationId: 1,
      currentLocationName: 'Floor',
      status: InventoryStatus.available,
      isArchived: false,
      createdAt: '2026-01-01T00:00:00Z',
      updatedAt: updatedAt,
    );

void main() {
  group('QA — Synchronization', () {
    const detector = ConflictDetector();

    test('detects inventory conflict when server updated_at differs', () {
      final conflict = detector.detectInventoryMutation(
        serverItem: _item('2026-06-02T00:00:00Z'),
        expectedUpdatedAt: '2026-06-01T00:00:00Z',
      );
      expect(conflict?.kind, SyncConflictKind.entityUpdatedOnServer);
    });

    test('sync state high-water marks detect entity changes', () {
      final previous = SyncStateSnapshot(
        serverTime: 't1',
        syncToken: 'a',
        highWaterMarks: const {'inventory': '1', 'sales': '1'},
        pollIntervalSeconds: 60,
        fetchedAt: DateTime.parse('2026-06-01T00:00:00Z'),
      );
      final current = SyncStateSnapshot(
        serverTime: 't2',
        syncToken: 'b',
        highWaterMarks: const {'inventory': '2', 'sales': '1'},
        pollIntervalSeconds: 60,
        fetchedAt: DateTime.parse('2026-06-02T00:00:00Z'),
      );
      expect(current.hasEntityChanges(previous), isTrue);
      expect(current.hasEntityChanges(current), isFalse);
    });

    test('pending operation round-trips through JSON', () {
      const factory = PendingOperationFactory();
      final op = factory.markSold(
        itemId: 'item-1',
        entityUpdatedAt: '2026-06-01T00:00:00Z',
        request: {
          'invoice_number': 'INV-1',
          'customer_name': 'Test',
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
