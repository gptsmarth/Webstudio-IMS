import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/constants/api_paths.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/json_map.dart';
import '../domain/audit_models.dart';

class AuditRepository {
  AuditRepository(this._api);

  final ApiClient _api;

  Future<List<AuditLogEntry>> listForInventoryItem(String inventoryItemId) async {
    return _api.get<List<AuditLogEntry>>(
      ApiPaths.auditLogsByInventory(inventoryItemId),
      parser: (json) => asJsonMapList(json).map(AuditLogEntry.fromJson).toList(),
    );
  }

  Future<List<AuditLogEntry>> lifecycleBySerial(String serial) async {
    return _api.get<List<AuditLogEntry>>(
      ApiPaths.auditLogsLifecycle(serial),
      parser: (json) => asJsonMapList(json).map(AuditLogEntry.fromJson).toList(),
    );
  }

  Future<PaginatedAuditResult> list({
    String? search,
    int page = 1,
    int pageSize = 50,
  }) async {
    final result = await _api.getPaginated(
      ApiPaths.auditLogs,
      queryParameters: {
        'page': page,
        'page_size': pageSize,
        if (search != null && search.trim().isNotEmpty) 'search': search.trim(),
      },
      itemParser: (json) => AuditLogEntry.fromJson(asJsonMap(json)),
    );
    return PaginatedAuditResult(
      items: result.items,
      page: result.page,
      totalPages: result.totalPages,
    );
  }
}

class PaginatedAuditResult {
  const PaginatedAuditResult({
    required this.items,
    required this.page,
    required this.totalPages,
  });

  final List<AuditLogEntry> items;
  final int page;
  final int totalPages;
}

final auditRepositoryProvider = Provider<AuditRepository>((ref) {
  return AuditRepository(ref.watch(apiClientProvider));
});
