import '../storage/hive_cache.dart';

class ApiCacheService {
  Future<void> put(String key, Map<String, dynamic> body) async {
    await HiveCache.apiCache.put(key, {
      'cached_at': DateTime.now().toUtc().toIso8601String(),
      'body': body,
    });
  }

  Map<String, dynamic>? get(String key) {
    final raw = HiveCache.apiCache.get(key);
    final body = raw?['body'];
    if (body is! Map) return null;
    return Map<String, dynamic>.from(body);
  }

  DateTime? cachedAt(String key) {
    final raw = HiveCache.apiCache.get(key);
    final value = raw?['cached_at'] as String?;
    return value == null ? null : DateTime.tryParse(value);
  }
}
