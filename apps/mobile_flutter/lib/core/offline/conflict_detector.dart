import '../../features/inventory/domain/inventory_models.dart';
import 'offline_models.dart';

class ConflictDetector {
  const ConflictDetector();

  SyncConflict? detectInventoryMutation({
    required InventoryItem? serverItem,
    required String? expectedUpdatedAt,
  }) {
    if (serverItem == null || expectedUpdatedAt == null) return null;
    if (serverItem.updatedAt != expectedUpdatedAt) {
      return SyncConflict(
        kind: SyncConflictKind.entityUpdatedOnServer,
        message: 'Inventory item changed on the server while this action was pending.',
        serverUpdatedAt: serverItem.updatedAt,
        localUpdatedAt: expectedUpdatedAt,
      );
    }
    return null;
  }

  bool inventoryHighWaterChanged({
    required SyncStateSnapshot current,
    required SyncStateSnapshot? previous,
  }) {
    return current.hasEntityChanges(previous);
  }
}
