import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';

import 'offline_models.dart';

class PendingOperationFactory {
  const PendingOperationFactory();

  static const _uuid = Uuid();

  PendingOperation transferLocation({
    required String itemId,
    required int locationId,
    required String entityUpdatedAt,
  }) {
    return PendingOperation(
      id: _uuid.v4(),
      type: PendingOperationType.transferLocation,
      entityId: itemId,
      entityUpdatedAt: entityUpdatedAt,
      payload: {'item_id': itemId, 'location_id': locationId},
      createdAt: DateTime.now().toUtc(),
    );
  }

  PendingOperation markSold({
    required String itemId,
    required String entityUpdatedAt,
    required Map<String, dynamic> request,
  }) {
    return PendingOperation(
      id: _uuid.v4(),
      type: PendingOperationType.markSold,
      entityId: itemId,
      entityUpdatedAt: entityUpdatedAt,
      payload: {'item_id': itemId, ...request},
      createdAt: DateTime.now().toUtc(),
    );
  }

  PendingOperation createInventory({
    required Map<String, dynamic> request,
  }) {
    return PendingOperation(
      id: _uuid.v4(),
      type: PendingOperationType.createInventory,
      payload: request,
      createdAt: DateTime.now().toUtc(),
    );
  }
}

final pendingOperationFactoryProvider = Provider<PendingOperationFactory>((_) => const PendingOperationFactory());
