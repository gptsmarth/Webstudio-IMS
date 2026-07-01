import 'package:flutter_test/flutter_test.dart';

import 'package:webstudio_ims/core/offline/conflict_detector.dart';
import 'package:webstudio_ims/core/offline/offline_models.dart';
import 'package:webstudio_ims/features/inventory/domain/inventory_models.dart';

InventoryItem _item({required String updatedAt}) {
  return InventoryItem(
    id: 'item-1',
    serialNumber: 'SN-1',
    productModelId: 'model-1',
    brandId: 1,
    brandName: 'Brand',
    modelNumber: 'M1',
    modelName: 'Model',
    cpu: 'i5',
    ramGb: 8,
    storageValue: '512',
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
}

void main() {
  group('ConflictDetector', () {
    const detector = ConflictDetector();

    test('detects server-side inventory updates', () {
      final conflict = detector.detectInventoryMutation(
        serverItem: _item(updatedAt: '2026-06-02T00:00:00Z'),
        expectedUpdatedAt: '2026-06-01T00:00:00Z',
      );
      expect(conflict?.kind, SyncConflictKind.entityUpdatedOnServer);
    });

    test('returns null when updatedAt matches', () {
      final conflict = detector.detectInventoryMutation(
        serverItem: _item(updatedAt: '2026-06-01T00:00:00Z'),
        expectedUpdatedAt: '2026-06-01T00:00:00Z',
      );
      expect(conflict, isNull);
    });
  });

  group('SyncStateSnapshot', () {
    test('detects high-water mark changes', () {
      final previous = SyncStateSnapshot(
        serverTime: 't1',
        syncToken: 'a',
        highWaterMarks: const {'inventory': '1'},
        pollIntervalSeconds: 60,
        fetchedAt: DateTime.parse('2026-06-01T00:00:00Z'),
      );
      final current = SyncStateSnapshot(
        serverTime: 't2',
        syncToken: 'b',
        highWaterMarks: const {'inventory': '2'},
        pollIntervalSeconds: 60,
        fetchedAt: DateTime.parse('2026-06-02T00:00:00Z'),
      );
      expect(current.hasEntityChanges(previous), isTrue);
      expect(current.hasEntityChanges(current), isFalse);
    });
  });
}
