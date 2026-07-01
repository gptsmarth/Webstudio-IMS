import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/user_repository.dart';
import '../domain/user_models.dart';

class UsersWorkspaceState {
  const UsersWorkspaceState({
    this.loading = false,
    this.error,
    this.items = const [],
    this.filters = const UsersListFilters(),
    this.totalItems = 0,
    this.totalPages = 1,
    this.selectedDetail,
    this.detailLoading = false,
  });

  final bool loading;
  final String? error;
  final List<UserSummary> items;
  final UsersListFilters filters;
  final int totalItems;
  final int totalPages;
  final UserDetail? selectedDetail;
  final bool detailLoading;

  UsersWorkspaceState copyWith({
    bool? loading,
    String? error,
    List<UserSummary>? items,
    UsersListFilters? filters,
    int? totalItems,
    int? totalPages,
    UserDetail? selectedDetail,
    bool? detailLoading,
    bool clearError = false,
    bool clearSelection = false,
  }) {
    return UsersWorkspaceState(
      loading: loading ?? this.loading,
      error: clearError ? null : error ?? this.error,
      items: items ?? this.items,
      filters: filters ?? this.filters,
      totalItems: totalItems ?? this.totalItems,
      totalPages: totalPages ?? this.totalPages,
      selectedDetail: clearSelection ? null : selectedDetail ?? this.selectedDetail,
      detailLoading: detailLoading ?? this.detailLoading,
    );
  }
}

final usersWorkspaceProvider =
    StateNotifierProvider<UsersWorkspaceController, UsersWorkspaceState>((ref) {
  return UsersWorkspaceController(ref);
});

class UsersWorkspaceController extends StateNotifier<UsersWorkspaceState> {
  UsersWorkspaceController(this._ref) : super(const UsersWorkspaceState());

  final Ref _ref;

  UserRepository get _users => _ref.read(userRepositoryProvider);

  Future<void> load() async {
    state = state.copyWith(loading: true, clearError: true);
    try {
      final result = await _users.listUsers(state.filters);
      state = state.copyWith(
        loading: false,
        items: result.items,
        totalItems: result.totalItems,
        totalPages: result.totalPages,
      );
    } catch (error) {
      state = state.copyWith(loading: false, error: error.toString());
    }
  }

  void setSearch(String value) {
    state = state.copyWith(filters: state.filters.copyWith(search: value, page: 1));
    _debouncedLoad();
  }

  void setPage(int page) {
    state = state.copyWith(filters: state.filters.copyWith(page: page));
    load();
  }

  Future<void> selectUser(int? id) async {
    if (id == null) {
      state = state.copyWith(clearSelection: true);
      return;
    }
    state = state.copyWith(detailLoading: true, clearSelection: false);
    try {
      final detail = await _users.getUser(id);
      state = state.copyWith(selectedDetail: detail, detailLoading: false);
    } catch (error) {
      state = state.copyWith(detailLoading: false, error: error.toString());
    }
  }

  void _debouncedLoad() {
    Future<void>.delayed(const Duration(milliseconds: 300), () {
      if (!mounted) return;
      load();
    });
  }

  Future<void> adminAction(Future<UserDetail> Function() action) async {
    state = state.copyWith(detailLoading: true, clearError: true);
    try {
      final detail = await action();
      await load();
      state = state.copyWith(selectedDetail: detail, detailLoading: false);
    } catch (error) {
      state = state.copyWith(detailLoading: false, error: error.toString());
    }
  }

  Future<void> resetPassword(int id, String password) async {
    state = state.copyWith(detailLoading: true, clearError: true);
    try {
      await _users.resetPassword(id, password);
      final detail = await _users.getUser(id);
      state = state.copyWith(selectedDetail: detail, detailLoading: false);
    } catch (error) {
      state = state.copyWith(detailLoading: false, error: error.toString());
    }
  }

  Future<void> disableUser(int id) => adminAction(() => _users.disableUser(id));
  Future<void> enableUser(int id) => adminAction(() => _users.enableUser(id));
  Future<void> unlockUser(int id) => adminAction(() => _users.unlockUser(id));
  Future<void> archiveUser(int id) => adminAction(() => _users.archiveUser(id));
  Future<void> restoreUser(int id) => adminAction(() => _users.restoreUser(id));

  Future<void> logoutAll(int id) async {
    state = state.copyWith(detailLoading: true);
    try {
      await _users.logoutAllSessions(id);
      final detail = await _users.getUser(id);
      state = state.copyWith(selectedDetail: detail, detailLoading: false);
    } catch (error) {
      state = state.copyWith(detailLoading: false, error: error.toString());
    }
  }

  Future<void> assignBuiltinAccess(int id, String role) => adminAction(
        () => _users.assignAccess(id, accessType: 'builtin', role: role),
      );

  Future<void> assignCustomAccess(int id, int customRoleId) => adminAction(
        () => _users.assignAccess(id, accessType: 'custom', customRoleId: customRoleId),
      );
}
