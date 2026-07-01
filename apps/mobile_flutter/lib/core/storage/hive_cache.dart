import 'package:hive_flutter/hive_flutter.dart';

/// Offline cache boxes — sync state, profile, and generic key-value cache.
class HiveCache {
  HiveCache._();

  static const syncStateBox = 'sync_state';
  static const profileBox = 'profile_cache';
  static const settingsBox = 'settings_cache';
  static const entityCacheBox = 'entity_cache';
  static const pendingOpsBox = 'pending_operations';
  static const apiCacheBox = 'api_cache';

  static Future<void> init() async {
    await Hive.initFlutter();
    await Future.wait([
      Hive.openBox<Map<String, dynamic>>(syncStateBox),
      Hive.openBox<Map<String, dynamic>>(profileBox),
      Hive.openBox<dynamic>(settingsBox),
      Hive.openBox<Map<String, dynamic>>(entityCacheBox),
      Hive.openBox<Map<String, dynamic>>(pendingOpsBox),
      Hive.openBox<Map<String, dynamic>>(apiCacheBox),
    ]);
  }

  static Box<Map<String, dynamic>> get syncState => Hive.box<Map<String, dynamic>>(syncStateBox);
  static Box<Map<String, dynamic>> get profile => Hive.box<Map<String, dynamic>>(profileBox);
  static Box<dynamic> get settings => Hive.box<dynamic>(settingsBox);
  static Box<Map<String, dynamic>> get entityCache => Hive.box<Map<String, dynamic>>(entityCacheBox);
  static Box<Map<String, dynamic>> get pendingOps => Hive.box<Map<String, dynamic>>(pendingOpsBox);
  static Box<Map<String, dynamic>> get apiCache => Hive.box<Map<String, dynamic>>(apiCacheBox);

  static Future<void> clearSensitive() async {
    await profile.clear();
    await syncState.clear();
  }

  static Future<void> clearEntityCaches() async {
    await entityCache.clear();
    await apiCache.clear();
  }
}
