import '../../features/dashboard/data/dashboard_repository.dart';
import '../../features/dashboard/domain/dashboard_models.dart';
import 'offline_cache_store.dart';
import 'offline_models.dart';

class DashboardCacheBundle {
  const DashboardCacheBundle({
    required this.snapshot,
    required this.distribution,
    required this.activity,
  });

  final OperationsDashboard snapshot;
  final DashboardDistribution distribution;
  final List<RecentActivityEntry> activity;
}

class OfflineDashboardService {
  OfflineDashboardService({
    required DashboardRepository dashboard,
    required OfflineCacheStore cache,
    required bool Function() isOnline,
  })  : _dashboard = dashboard,
        _cache = cache,
        _isOnline = isOnline;

  final DashboardRepository _dashboard;
  final OfflineCacheStore _cache;
  final bool Function() _isOnline;

  Future<OfflineLoadResult<DashboardCacheBundle>> loadDashboard({bool forceRefresh = false}) async {
    if (_isOnline()) {
      try {
        final fresh = await _fetchAndCache();
        return OfflineLoadResult(data: fresh, fromCache: false, isStale: false);
      } catch (error) {
        final cached = _readCache();
        if (cached != null) {
          return OfflineLoadResult(data: cached, fromCache: true, isStale: true, error: error.toString());
        }
        rethrow;
      }
    }

    final cached = _readCache();
    if (cached == null) {
      throw StateError('No cached dashboard data available offline.');
    }
    return OfflineLoadResult(data: cached, fromCache: true, isStale: true);
  }

  Future<DashboardCacheBundle> _fetchAndCache() async {
    final results = await Future.wait([
      _dashboard.getSnapshot(),
      _dashboard.getDistribution(),
      _dashboard.getRecentActivity(limit: 10),
    ]);
    final bundle = DashboardCacheBundle(
      snapshot: results[0] as OperationsDashboard,
      distribution: results[1] as DashboardDistribution,
      activity: results[2] as List<RecentActivityEntry>,
    );
    await _cache.putMap(OfflineCacheKeys.dashboardSnapshot, {
      'total_available_inventory': bundle.snapshot.totalAvailableInventory,
      'as_of': bundle.snapshot.asOf,
    });
    await _cache.putMap(OfflineCacheKeys.dashboardDistribution, {
      'total_available_inventory': bundle.distribution.totalAvailableInventory,
      'by_brand': bundle.distribution.byBrand
          .map((g) => {'id': g.id, 'name': g.name, 'available': g.available, 'sold': g.sold, 'total': g.total})
          .toList(),
      'by_location': bundle.distribution.byLocation
          .map((g) => {'id': g.id, 'name': g.name, 'available': g.available, 'sold': g.sold, 'total': g.total})
          .toList(),
      'by_product_model': bundle.distribution.byProductModel
          .map((g) => {'id': g.id, 'name': g.name, 'available': g.available, 'sold': g.sold, 'total': g.total})
          .toList(),
      'as_of': bundle.distribution.asOf,
    });
    await _cache.putList(
      OfflineCacheKeys.dashboardActivity,
      bundle.activity
          .map((entry) => {
                'id': entry.id,
                'activity_type': entry.activityType,
                'description': entry.description,
                'actor_display_name': entry.actorDisplayName,
                'created_at': entry.createdAt,
              })
          .toList(),
    );
    return bundle;
  }

  DashboardCacheBundle? _readCache() {
    final snapshotRaw = _cache.readMap(OfflineCacheKeys.dashboardSnapshot);
    final distributionRaw = _cache.readMap(OfflineCacheKeys.dashboardDistribution);
    final activityRaw = _cache.readList(OfflineCacheKeys.dashboardActivity);
    if (snapshotRaw == null || distributionRaw == null || activityRaw == null) return null;
    return DashboardCacheBundle(
      snapshot: OperationsDashboard.fromJson(snapshotRaw.data),
      distribution: DashboardDistribution.fromJson(distributionRaw.data),
      activity: activityRaw.data.map((json) => RecentActivityEntry.fromJson(json)).toList(),
    );
  }
}
