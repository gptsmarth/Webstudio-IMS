import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/constants/api_paths.dart';
import '../../../core/network/api_client.dart';
import '../../../shared/models/downloaded_file.dart';
import '../domain/tally_models.dart';

class TallySyncHistoryFilters {
  const TallySyncHistoryFilters({
    this.status,
    this.dateFrom,
    this.dateTo,
    this.search,
    this.limit = 100,
    this.offset = 0,
  });

  final String? status;
  final String? dateFrom;
  final String? dateTo;
  final String? search;
  final int limit;
  final int offset;

  Map<String, dynamic> toQuery() {
    return {
      if (status != null && status!.isNotEmpty) 'status': status,
      if (dateFrom != null && dateFrom!.isNotEmpty) 'date_from': dateFrom,
      if (dateTo != null && dateTo!.isNotEmpty) 'date_to': dateTo,
      if (search != null && search!.isNotEmpty) 'search': search,
      'limit': limit,
      'offset': offset,
    };
  }
}

class TallyRepository {
  TallyRepository(this._api);

  final ApiClient _api;

  Future<TallyDashboardData> getDashboard() async {
    return _api.get(
      ApiPaths.tallyDashboard,
      parser: (json) => TallyDashboardData.fromJson(Map<String, dynamic>.from(json! as Map)),
    );
  }

  Future<List<TallySyncHistoryEntry>> getSyncHistory([TallySyncHistoryFilters? filters]) async {
    final query = filters?.toQuery() ?? const {'limit': 100};
    return _api.get(
      ApiPaths.tallySyncHistory,
      queryParameters: query,
      parser: (json) {
        final list = json as List<dynamic>? ?? const [];
        return list
            .whereType<Map<String, dynamic>>()
            .map(TallySyncHistoryEntry.fromJson)
            .toList();
      },
    );
  }

  Future<DownloadedFile> exportSyncHistory([TallySyncHistoryFilters? filters]) {
    final query = filters?.toQuery() ?? const {};
    return _api.downloadBytes(
      ApiPaths.tallySyncHistoryExport,
      queryParameters: query,
      fallbackFilename: 'tally-sync-history.csv',
    );
  }

  Future<Map<String, dynamic>> triggerSync() async {
    return _api.post(
      ApiPaths.tallySyncTrigger,
      data: const {},
      parser: (json) => Map<String, dynamic>.from(json! as Map),
    );
  }

  Future<Map<String, dynamic>> retrySync() async {
    return _api.post(
      ApiPaths.tallySyncRetry,
      data: const {},
      parser: (json) => Map<String, dynamic>.from(json! as Map),
    );
  }

  Future<Map<String, dynamic>> testConnection() async {
    return _api.post(
      ApiPaths.tallyConnectionTest,
      data: const {},
      parser: (json) => Map<String, dynamic>.from(json! as Map),
    );
  }
}

final tallyRepositoryProvider = Provider<TallyRepository>((ref) {
  return TallyRepository(ref.watch(apiClientProvider));
});

final tallyDashboardProvider = FutureProvider.autoDispose<TallyDashboardData>((ref) async {
  return ref.watch(tallyRepositoryProvider).getDashboard();
});

final tallySyncHistoryProvider = FutureProvider.autoDispose
    .family<List<TallySyncHistoryEntry>, TallySyncHistoryFilters>((ref, filters) async {
  return ref.watch(tallyRepositoryProvider).getSyncHistory(filters);
});
