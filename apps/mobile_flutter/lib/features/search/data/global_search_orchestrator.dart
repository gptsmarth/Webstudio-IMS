import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/constants/api_paths.dart';
import '../../../core/network/api_client.dart';
import '../../../core/routing/app_routes.dart';
import '../../audit/data/audit_repository.dart';
import '../../notifications/data/notification_repository.dart';
import '../../sales/data/sales_repository.dart';
import '../../sales/domain/sales_models.dart';
import '../data/search_repository.dart';
import '../domain/search_models.dart';

/// Desktop-parity global search: unified API plus permission-gated module fetches.
class GlobalSearchOrchestrator {
  GlobalSearchOrchestrator({
    required SearchRepository search,
    required SalesRepository sales,
    required AuditRepository audit,
    required NotificationRepository notifications,
    required ApiClient api,
  })  : _search = search,
        _sales = sales,
        _audit = audit,
        _notifications = notifications,
        _api = api;

  final SearchRepository _search;
  final SalesRepository _sales;
  final AuditRepository _audit;
  final NotificationRepository _notifications;
  final ApiClient _api;

  Future<GlobalSearchResult> searchAll(String query, {required List<String> permissions, int limit = 12}) async {
    final term = query.trim();
    if (term.length < 2) return GlobalSearchResult(query: term, hits: const []);

    final hits = <GlobalSearchHit>[];
    final base = await _search.search(term, limit: limit);
    hits.addAll(base.hits);

    if (permissions.contains('sales:view')) {
      try {
        final sales = await _sales.listSales(
          filters: const SalesListFilters(),
          page: 1,
          pageSize: limit,
          search: term,
          sortField: SalesSortField.soldAt,
          sortDirection: 'desc',
        );
        for (final sale in sales.items) {
          hits.add(GlobalSearchHit(
            type: 'sale',
            id: '${sale.id}',
            title: sale.invoiceNumber,
            subtitle: '${sale.customerName ?? '—'} · ${sale.serialNumber}',
            routeHint: '/sales',
          ));
        }
      } catch (_) {}
    }

    if (permissions.contains('audit:view')) {
      try {
        final audit = await _audit.list(search: term, page: 1, pageSize: limit);
        for (final entry in audit.items) {
          hits.add(GlobalSearchHit(
            type: 'audit',
            id: '${entry.id}',
            title: entry.description,
            subtitle: '${entry.module} · ${entry.operation}',
            routeHint: '/more/audit',
          ));
        }
      } catch (_) {}
    }

    if (permissions.contains('notifications:view')) {
      try {
        final notes = await _notifications.listNotifications(page: 1, pageSize: limit);
        for (final note in notes.items.where((n) => n.title.toLowerCase().contains(term.toLowerCase()))) {
          hits.add(GlobalSearchHit(
            type: 'notification',
            id: '${note.id}',
            title: note.title,
            subtitle: note.description,
            routeHint: '/more/notifications',
          ));
        }
      } catch (_) {}
    }

    if (permissions.contains('users:view')) {
      try {
        final users = await _api.getPaginated(
          ApiPaths.users,
          queryParameters: {'search': term, 'page': 1, 'page_size': limit},
          itemParser: (json) => json! as Map<String, dynamic>,
        );
        for (final user in users.items) {
          hits.add(GlobalSearchHit(
            type: 'user',
            id: '${user['id']}',
            title: user['display_name']?.toString() ?? user['username']?.toString() ?? 'User',
            subtitle: user['role']?.toString() ?? '',
            routeHint: AppRoutes.settingsUsers,
          ));
        }
      } catch (_) {}
    }

    return GlobalSearchResult(query: term, hits: hits.take(limit * 3).toList());
  }
}

final globalSearchOrchestratorProvider = Provider<GlobalSearchOrchestrator>((ref) {
  return GlobalSearchOrchestrator(
    search: ref.watch(searchRepositoryProvider),
    sales: ref.watch(salesRepositoryProvider),
    audit: ref.watch(auditRepositoryProvider),
    notifications: ref.watch(notificationRepositoryProvider),
    api: ref.watch(apiClientProvider),
  );
});
