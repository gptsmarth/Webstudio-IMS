import '../network/json_map.dart';
import '../storage/hive_cache.dart';

class ApiCacheService {
  Future<void> put(String key, Map<String, dynamic> body) async {
    await HiveCache.apiCache.put(key, {
      'cached_at': DateTime.now().toUtc().toIso8601String(),
      'body': body,
    });
  }

  Map<String, dynamic>? get(String key) {
    final raw = HiveCache.readMap(HiveCache.apiCache, key);
    return asJsonMapOrNull(raw?['body']);
  }

  DateTime? cachedAt(String key) {
    final raw = HiveCache.readMap(HiveCache.apiCache, key);
    final value = raw?['cached_at'] as String?;
    return value == null ? null : DateTime.tryParse(value);
  }
}
