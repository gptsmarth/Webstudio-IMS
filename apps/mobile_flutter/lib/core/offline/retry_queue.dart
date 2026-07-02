import '../../features/inventory/data/inventory_repository.dart';
import '../../features/inventory/domain/inventory_models.dart';
import 'conflict_detector.dart';
import 'offline_models.dart';
import 'pending_operations_store.dart';

class RetryQueue {
  RetryQueue({
    required PendingOperationsStore store,
    required InventoryRepository inventory,
    required ConflictDetector conflicts,
    this.maxAttempts = 3,
  })  : _store = store,
        _inventory = inventory,
        _conflicts = conflicts;

  final PendingOperationsStore _store;
  final InventoryRepository _inventory;
  final ConflictDetector _conflicts;
  final int maxAttempts;

  Future<RetryQueueResult> processAll({void Function(int completed, int total)? onProgress}) async {
    final operations = _store.listAll();
    final actionable = operations.where((op) => !op.hasConflict && op.attemptCount < maxAttempts).length;
    var applied = 0;
    var failed = 0;
    var conflicts = 0;
    var processed = 0;

    for (final operation in operations) {
      if (operation.hasConflict) {
        conflicts += 1;
        continue;
      }
      if (operation.attemptCount >= maxAttempts) {
        failed += 1;
        continue;
      }

      try {
        final conflict = await _apply(operation);
        if (conflict != null) {
          await _store.update(operation.copyWith(conflict: conflict));
          conflicts += 1;
          continue;
        }
        await _store.remove(operation.id);
        applied += 1;
        processed += 1;
        onProgress?.call(processed, actionable);
      } catch (error) {
        await _store.update(
          operation.copyWith(
            attemptCount: operation.attemptCount + 1,
            lastError: error.toString(),
          ),
        );
        failed += 1;
        processed += 1;
        onProgress?.call(processed, actionable);
      }
    }

    return RetryQueueResult(applied: applied, failed: failed, conflicts: conflicts);
  }

  Future<SyncConflict?> _apply(PendingOperation operation) async {
    switch (operation.type) {
      case PendingOperationType.transferLocation:
        final itemId = operation.entityId ?? operation.payload['item_id'] as String;
        final locationId = operation.payload['location_id'] as int;
        final serverItem = await _inventory.getItem(itemId);
        final conflict = _conflicts.detectInventoryMutation(
          serverItem: serverItem,
          expectedUpdatedAt: operation.entityUpdatedAt,
        );
        if (conflict != null) return conflict;
        await _inventory.transferLocation(itemId, locationId);
        return null;
      case PendingOperationType.markSold:
        final itemId = operation.entityId ?? operation.payload['item_id'] as String;
        final request = MarkSoldRequest(
          invoiceNumber: operation.payload['invoice_number'] as String,
          customerName: operation.payload['customer_name'] as String,
          paymentMode: operation.payload['payment_mode'] as String,
          saleDate: operation.payload['sale_date'] as String,
          saleAmount: (operation.payload['sale_amount'] as num?)?.toDouble(),
          remarks: operation.payload['remarks'] as String?,
        );
        final serverItem = await _inventory.getItem(itemId);
        final conflict = _conflicts.detectInventoryMutation(
          serverItem: serverItem,
          expectedUpdatedAt: operation.entityUpdatedAt,
        );
        if (conflict != null) return conflict;
        await _inventory.markSold(itemId, request);
        return null;
      case PendingOperationType.createInventory:
        final request = CreateInventoryItemRequest(
          serialNumber: operation.payload['serial_number'] as String,
          productModelId: operation.payload['product_model_id'] as String,
          color: operation.payload['color'] as String,
          currentLocationId: operation.payload['current_location_id'] as int,
        );
        await _inventory.createItem(request);
        return null;
    }
  }
}

class RetryQueueResult {
  const RetryQueueResult({
    required this.applied,
    required this.failed,
    required this.conflicts,
  });

  final int applied;
  final int failed;
  final int conflicts;
}
