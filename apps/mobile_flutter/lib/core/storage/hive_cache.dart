import 'package:hive_flutter/hive_flutter.dart';

import '../network/json_map.dart';

/// Offline cache boxes — sync state, profile, and generic key-value cache.
///
/// Boxes are opened as `Box<dynamic>` (not `Box<Map<String, dynamic>>`) because
/// Hive deserializes maps as `Map<dynamic, dynamic>`. Typed boxes cast on
/// [Box.get] and crash startup with:
/// `type '_Map<dynamic, dynamic>' is not a subtype of type 'Map<String, dynamic>?'`.
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
      Hive.openBox<dynamic>(syncStateBox),
      Hive.openBox<dynamic>(profileBox),
      Hive.openBox<dynamic>(settingsBox),
      Hive.openBox<dynamic>(entityCacheBox),
      Hive.openBox<dynamic>(pendingOpsBox),
      Hive.openBox<dynamic>(apiCacheBox),
    ]);
  }

  static Box<dynamic> get syncState => Hive.box<dynamic>(syncStateBox);
  static Box<dynamic> get profile => Hive.box<dynamic>(profileBox);
  static Box<dynamic> get settings => Hive.box<dynamic>(settingsBox);
  static Box<dynamic> get entityCache => Hive.box<dynamic>(entityCacheBox);
  static Box<dynamic> get pendingOps => Hive.box<dynamic>(pendingOpsBox);
  static Box<dynamic> get apiCache => Hive.box<dynamic>(apiCacheBox);

  /// Safe map read — coerces Hive's `Map<dynamic, dynamic>` without type casts.
  static Map<String, dynamic>? readMap(Box<dynamic> box, Object key) {
    return asJsonMapOrNull(box.get(key));
  }

  static Future<void> clearSensitive() async {
    await profile.clear();
    await syncState.clear();
  }

  static Future<void> clearEntityCaches() async {
    await entityCache.clear();
    await apiCache.clear();
  }
}
