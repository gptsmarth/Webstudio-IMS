import 'package:flutter_test/flutter_test.dart';

import 'package:webstudio_ims/core/offline/offline_cache_store.dart';
import 'package:webstudio_ims/core/offline/offline_models.dart';
import 'package:webstudio_ims/core/offline/pending_operation_factory.dart';

void main() {
  group('QA — Offline', () {
    test('offline cache keys are namespaced', () {
      expect(OfflineCacheKeys.inventoryItems, 'inventory:items');
      expect(OfflineCacheKeys.dashboardSnapshot, 'dashboard:snapshot');
      expect(OfflineCacheKeys.syncState, 'sync:state');
    });

    test('cached payload tracks age', () {
      final payload = CachedPayload(
        data: const ['a'],
        cachedAt: DateTime.now().subtract(const Duration(hours: 2)),
      );
      expect(payload.isOlderThan(const Duration(hours: 1)), isTrue);
      expect(payload.isOlderThan(const Duration(hours: 3)), isFalse);
    });

    test('offline load result flags stale cache', () {
      const result = OfflineLoadResult(
        data: 'ok',
        fromCache: true,
        isStale: true,
        error: 'Network unavailable',
      );
      expect(result.fromCache, isTrue);
      expect(result.isStale, isTrue);
    });

    test('pending transfer operation captures entity snapshot', () {
      const factory = PendingOperationFactory();
      final op = factory.transferLocation(
        itemId: 'item-1',
        locationId: 3,
        entityUpdatedAt: '2026-06-01T00:00:00Z',
      );
      expect(op.type, PendingOperationType.transferLocation);
      expect(op.entityUpdatedAt, '2026-06-01T00:00:00Z');
    });
  });
}
