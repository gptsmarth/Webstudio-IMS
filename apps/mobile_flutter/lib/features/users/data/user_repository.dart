import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/constants/api_paths.dart';
import '../../../core/network/api_client.dart';
import '../../../shared/models/pagination.dart';
import '../domain/user_models.dart';

class UserRepository {
  UserRepository(this._api);

  final ApiClient _api;

  Future<PaginatedResult<UserSummary>> listUsers(UsersListFilters filters) async {
    return _api.getPaginated(
      ApiPaths.users,
      queryParameters: filters.toQueryParams(),
      itemParser: (json) => UserSummary.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<UserDetail> getUser(int id) async {
    return _api.get(
      '${ApiPaths.users}/$id',
      parser: (json) => UserDetail.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<UserDetail> createUser(Map<String, dynamic> data) async {
    return _api.post(
      ApiPaths.users,
      data: data,
      parser: (json) => UserDetail.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<UserDetail> updateUser(int id, Map<String, dynamic> data) async {
    return _api.patch(
      '${ApiPaths.users}/$id',
      data: data,
      parser: (json) => UserDetail.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<void> resetPassword(int id, String newPassword) async {
    await _api.post(
      '${ApiPaths.users}/$id/reset-password',
      data: {'temporary_password': newPassword},
      parser: (_) => null,
    );
  }

  Future<UserDetail> disableUser(int id) async {
    return _api.post(
      '${ApiPaths.users}/$id/disable',
      data: const {},
      parser: (json) => UserDetail.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<UserDetail> enableUser(int id) async {
    return _api.post(
      '${ApiPaths.users}/$id/enable',
      data: const {},
      parser: (json) => UserDetail.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<UserDetail> unlockUser(int id) async {
    return _api.post(
      '${ApiPaths.users}/$id/unlock',
      data: const {},
      parser: (json) => UserDetail.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<void> logoutAllSessions(int id) async {
    await _api.post(
      '${ApiPaths.users}/$id/logout-all',
      data: const {},
      parser: (_) => null,
    );
  }

  Future<UserDetail> assignAccess(
    int id, {
    required String accessType,
    String? role,
    int? customRoleId,
  }) async {
    return _api.patch(
      '${ApiPaths.users}/$id/access',
      data: {
        'access_type': accessType,
        if (role != null) 'role': role,
        if (customRoleId != null) 'custom_role_id': customRoleId,
      },
      parser: (json) => UserDetail.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<UserDetail> archiveUser(int id) async {
    return _api.post(
      '${ApiPaths.users}/$id/archive',
      data: const {},
      parser: (json) => UserDetail.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<UserDetail> restoreUser(int id) async {
    return _api.post(
      '${ApiPaths.users}/$id/restore',
      data: const {},
      parser: (json) => UserDetail.fromJson(json! as Map<String, dynamic>),
    );
  }
}

final userRepositoryProvider = Provider<UserRepository>((ref) {
  return UserRepository(ref.watch(apiClientProvider));
});
