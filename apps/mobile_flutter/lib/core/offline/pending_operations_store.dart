import '../storage/hive_cache.dart';
import 'offline_models.dart';

class PendingOperationsStore {
  static const _indexKey = '__index__';

  Future<void> enqueue(PendingOperation operation) async {
    await HiveCache.pendingOps.put(operation.id, operation.toJson());
    final index = _readIndex();
    if (!index.contains(operation.id)) {
      index.add(operation.id);
      await HiveCache.pendingOps.put(_indexKey, {'ids': index});
    }
  }

  Future<void> update(PendingOperation operation) async {
    await HiveCache.pendingOps.put(operation.id, operation.toJson());
  }

  Future<void> remove(String id) async {
    await HiveCache.pendingOps.delete(id);
    final index = _readIndex()..remove(id);
    await HiveCache.pendingOps.put(_indexKey, {'ids': index});
  }

  List<PendingOperation> listAll() {
    final ids = _readIndex();
    final operations = <PendingOperation>[];
    for (final id in ids) {
      final raw = HiveCache.readMap(HiveCache.pendingOps, id);
      if (raw == null) continue;
      operations.add(PendingOperation.fromJson(raw));
    }
    operations.sort((a, b) => a.createdAt.compareTo(b.createdAt));
    return operations;
  }

  int get count => _readIndex().length;

  int get conflictCount => listAll().where((op) => op.hasConflict).length;

  List<String> _readIndex() {
    final raw = HiveCache.readMap(HiveCache.pendingOps, _indexKey);
    final ids = raw?['ids'];
    if (ids is! List) return <String>[];
    return ids.map((id) => id.toString()).toList();
  }
}
