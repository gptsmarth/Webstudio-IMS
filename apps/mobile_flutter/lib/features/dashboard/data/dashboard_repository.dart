import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/constants/api_paths.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/json_map.dart';
import '../domain/dashboard_models.dart';

class DashboardRepository {
  DashboardRepository(this._api);

  final ApiClient _api;

  Future<OperationsDashboard> getSnapshot() async {
    return _api.get(
      ApiPaths.dashboard,
      parser: (json) => OperationsDashboard.fromJson(asJsonMap(json)),
    );
  }

  Future<DashboardDistribution> getDistribution() async {
    return _api.get(
      ApiPaths.dashboardDistribution,
      parser: (json) => DashboardDistribution.fromJson(asJsonMap(json)),
    );
  }

  Future<List<RecentActivityEntry>> getRecentActivity({int limit = 12}) async {
    return _api.get<List<RecentActivityEntry>>(
      ApiPaths.dashboardRecentActivity,
      queryParameters: {'limit': limit},
      parser: (json) {
        return asJsonMapList(json).map(RecentActivityEntry.fromJson).toList();
      },
    );
  }
}

final dashboardRepositoryProvider = Provider<DashboardRepository>((ref) {
  return DashboardRepository(ref.watch(apiClientProvider));
});
