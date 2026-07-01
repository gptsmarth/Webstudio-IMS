import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/constants/api_paths.dart';
import '../../../core/network/api_client.dart';
import '../../../shared/models/pagination.dart';
import '../domain/notification_models.dart';

class NotificationRepository {
  NotificationRepository(this._api);

  final ApiClient _api;

  Future<PaginatedResult<NotificationItem>> listNotifications({
    bool isResolved = false,
    int page = 1,
    int pageSize = 100,
  }) async {
    return _api.getPaginated(
      ApiPaths.notifications,
      queryParameters: {
        'is_resolved': isResolved,
        'page': page,
        'page_size': pageSize,
      },
      itemParser: (json) => NotificationItem.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<void> markRead(int id) async {
    await _api.patch<Object?>(
      '${ApiPaths.notifications}/$id/read',
      data: const {},
      parser: (_) => null,
    );
  }

  Future<void> resolve(int id) async {
    await _api.patch<Object?>(
      '${ApiPaths.notifications}/$id/resolve',
      data: const {},
      parser: (_) => null,
    );
  }
}

final notificationRepositoryProvider = Provider<NotificationRepository>((ref) {
  return NotificationRepository(ref.watch(apiClientProvider));
});
