import '../storage/hive_cache.dart';
import '../network/json_map.dart';
import 'offline_models.dart';

class OfflineCacheKeys {
  static const inventoryItems = 'inventory:items';
  static const inventoryBrands = 'inventory:brands';
  static const inventoryModels = 'inventory:models';
  static const inventoryLocations = 'inventory:locations';
  static const inventoryDistribution = 'inventory:distribution';
  static const dashboardSnapshot = 'dashboard:snapshot';
  static const dashboardDistribution = 'dashboard:distribution';
  static const dashboardActivity = 'dashboard:activity';
  static const salesList = 'sales:list';
  static const catalogueBrands = 'catalogue:brands';
  static const catalogueModels = 'catalogue:models';
  static const catalogueLocations = 'catalogue:locations';
  static const reportsRecent = 'reports:recent';
  static const notificationsList = 'notifications:list';
  static const settingsSnapshot = 'settings:snapshot';
  static const syncState = 'sync:state';
}

class OfflineCacheStore {
  Future<void> putList(String key, List<Map<String, dynamic>> items) async {
    await HiveCache.entityCache.put(key, {
      'cached_at': DateTime.now().toUtc().toIso8601String(),
      'data': items,
    });
  }

  Future<void> putMap(String key, Map<String, dynamic> value) async {
    await HiveCache.entityCache.put(key, {
      'cached_at': DateTime.now().toUtc().toIso8601String(),
      'data': value,
    });
  }

  CachedPayload<List<Map<String, dynamic>>>? readList(String key) {
    final raw = HiveCache.entityCache.get(key);
    if (raw == null) return null;
    final data = raw['data'];
    final cachedAt = raw['cached_at'] as String?;
    if (data is! List || cachedAt == null) return null;
    final items = asJsonMapList(data);
    if (items.isEmpty && data.isNotEmpty) return null;
    return CachedPayload(data: items, cachedAt: DateTime.parse(cachedAt));
  }

  CachedPayload<Map<String, dynamic>>? readMap(String key) {
    final raw = HiveCache.entityCache.get(key);
    if (raw == null) return null;
    final data = raw['data'];
    final cachedAt = raw['cached_at'] as String?;
    if (data is! Map || cachedAt == null) return null;
    return CachedPayload(
      data: Map<String, dynamic>.from(data),
      cachedAt: DateTime.parse(cachedAt),
    );
  }

  DateTime? lastCachedAt(String key) {
    final raw = HiveCache.entityCache.get(key);
    final cachedAt = raw?['cached_at'] as String?;
    return cachedAt == null ? null : DateTime.tryParse(cachedAt);
  }
}
