import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/device/push_notification_service.dart';
import '../data/notification_repository.dart';
import '../domain/notification_models.dart';

class NotificationsWorkspaceState {
  const NotificationsWorkspaceState({
    this.loading = false,
    this.error,
    this.items = const [],
    this.search = '',
    this.severityFilter,
    this.actionInProgress = false,
  });

  final bool loading;
  final String? error;
  final List<NotificationItem> items;
  final String search;
  final NotificationSeverity? severityFilter;
  final bool actionInProgress;

  List<NotificationItem> get visibleItems {
    var pool = items;
    if (severityFilter != null) {
      pool = pool.where((item) => item.severity == severityFilter).toList();
    }
    final term = search.trim().toLowerCase();
    if (term.isEmpty) return pool;
    return pool
        .where((item) =>
            item.title.toLowerCase().contains(term) ||
            item.description.toLowerCase().contains(term) ||
            (item.serialNumber?.toLowerCase().contains(term) ?? false))
        .toList();
  }

  int get unreadCount => items.where((item) => !item.isRead).length;

  NotificationsWorkspaceState copyWith({
    bool? loading,
    String? error,
    List<NotificationItem>? items,
    String? search,
    NotificationSeverity? severityFilter,
    bool? actionInProgress,
    bool clearError = false,
    bool clearSeverity = false,
  }) {
    return NotificationsWorkspaceState(
      loading: loading ?? this.loading,
      error: clearError ? null : error ?? this.error,
      items: items ?? this.items,
      search: search ?? this.search,
      severityFilter: clearSeverity ? null : severityFilter ?? this.severityFilter,
      actionInProgress: actionInProgress ?? this.actionInProgress,
    );
  }
}

final notificationsWorkspaceProvider =
    StateNotifierProvider<NotificationsWorkspaceController, NotificationsWorkspaceState>((ref) {
  return NotificationsWorkspaceController(ref);
});

class NotificationsWorkspaceController extends StateNotifier<NotificationsWorkspaceState> {
  NotificationsWorkspaceController(this._ref) : super(const NotificationsWorkspaceState());

  final Ref _ref;
  int _lastKnownUnread = 0;
  bool _hasBaseline = false;

  NotificationRepository get _repo => _ref.read(notificationRepositoryProvider);

  Future<void> load() async {
    state = state.copyWith(loading: true, clearError: true);
    try {
      final result = await _repo.listNotifications();
      final unread = result.items.where((item) => !item.isRead).length;
      if (_hasBaseline && unread > _lastKnownUnread) {
        final latestUnread = result.items.firstWhere(
          (item) => !item.isRead,
          orElse: () => result.items.first,
        );
        await _ref.read(backgroundNotificationCoordinatorProvider).notifyNewAlerts(
              unreadCount: unread - _lastKnownUnread,
              latestTitle: latestUnread.title,
            );
      }
      _lastKnownUnread = unread;
      _hasBaseline = true;
      state = state.copyWith(loading: false, items: result.items);
    } catch (error) {
      state = state.copyWith(loading: false, error: error.toString());
    }
  }

  void setSearch(String value) => state = state.copyWith(search: value);
  void setSeverity(NotificationSeverity? severity) =>
      state = state.copyWith(severityFilter: severity, clearSeverity: severity == null);

  Future<void> markRead(int id) async {
    state = state.copyWith(actionInProgress: true, clearError: true);
    try {
      await _repo.markRead(id);
      await load();
      state = state.copyWith(actionInProgress: false);
    } catch (error) {
      state = state.copyWith(actionInProgress: false, error: error.toString());
    }
  }

  Future<void> resolve(int id) async {
    state = state.copyWith(actionInProgress: true, clearError: true);
    try {
      await _repo.resolve(id);
      await load();
      state = state.copyWith(actionInProgress: false);
    } catch (error) {
      state = state.copyWith(actionInProgress: false, error: error.toString());
    }
  }
}
