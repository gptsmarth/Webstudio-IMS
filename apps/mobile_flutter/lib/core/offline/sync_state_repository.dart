import '../constants/api_paths.dart';
import '../network/api_client.dart';
import '../storage/hive_cache.dart';
import 'offline_cache_store.dart';
import 'offline_models.dart';

class SyncStateRepository {
  SyncStateRepository(this._api, this._cache);

  final ApiClient _api;
  final OfflineCacheStore _cache;

  Future<SyncStateSnapshot> fetchRemote() async {
    final payload = await _api.get<Map<String, dynamic>>(
      ApiPaths.syncState,
      parser: (json) => Map<String, dynamic>.from(json! as Map),
    );
    final snapshot = SyncStateSnapshot.fromApi(payload);
    await _cache.putMap(OfflineCacheKeys.syncState, snapshot.toJson());
    await HiveCache.syncState.put('latest', snapshot.toJson());
    return snapshot;
  }

  SyncStateSnapshot? readLocal() {
    final cached = _cache.readMap(OfflineCacheKeys.syncState);
    if (cached != null) return SyncStateSnapshot.fromJson(cached.data);
    final legacy = HiveCache.syncState.get('latest');
    if (legacy == null) return null;
    return SyncStateSnapshot.fromJson(Map<String, dynamic>.from(legacy));
  }
}
