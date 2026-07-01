import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/constants/api_paths.dart';
import '../../../core/network/api_client.dart';

class AccessRoleSummary {
  const AccessRoleSummary({
    required this.id,
    required this.name,
    this.description,
    required this.isActive,
    required this.permissionCount,
    required this.assignedUserCount,
  });

  final int id;
  final String name;
  final String? description;
  final bool isActive;
  final int permissionCount;
  final int assignedUserCount;

  factory AccessRoleSummary.fromJson(Map<String, dynamic> json) {
    return AccessRoleSummary(
      id: json['id'] as int,
      name: json['name'] as String,
      description: json['description'] as String?,
      isActive: json['is_active'] as bool? ?? true,
      permissionCount: json['permission_count'] as int? ?? 0,
      assignedUserCount: json['assigned_user_count'] as int? ?? 0,
    );
  }
}

class AccessRoleDetail extends AccessRoleSummary {
  const AccessRoleDetail({
    required super.id,
    required super.name,
    super.description,
    required super.isActive,
    required super.permissionCount,
    required super.assignedUserCount,
    required this.permissions,
  });

  final List<String> permissions;

  factory AccessRoleDetail.fromJson(Map<String, dynamic> json) {
    final summary = AccessRoleSummary.fromJson(json);
    return AccessRoleDetail(
      id: summary.id,
      name: summary.name,
      description: summary.description,
      isActive: summary.isActive,
      permissionCount: summary.permissionCount,
      assignedUserCount: summary.assignedUserCount,
      permissions: (json['permissions'] as List<dynamic>? ?? const [])
          .map((entry) => entry.toString())
          .toList(),
    );
  }
}

class AccessRoleRepository {
  AccessRoleRepository(this._api);

  final ApiClient _api;

  Future<List<AccessRoleSummary>> listRoles({bool includeInactive = false}) async {
    return _api.get(
      ApiPaths.accessRoles,
      queryParameters: {'include_inactive': includeInactive},
      parser: (json) => (json as List<dynamic>? ?? const [])
          .map((entry) => AccessRoleSummary.fromJson(entry as Map<String, dynamic>))
          .toList(),
    );
  }

  Future<AccessRoleDetail> getRole(int id) async {
    return _api.get(
      '${ApiPaths.accessRoles}/$id',
      parser: (json) => AccessRoleDetail.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<AccessRoleDetail> createRole({
    required String name,
    String? description,
    required List<String> permissions,
  }) async {
    return _api.post(
      ApiPaths.accessRoles,
      data: {'name': name, 'description': description, 'permissions': permissions},
      parser: (json) => AccessRoleDetail.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<AccessRoleDetail> updateRole(
    int id, {
    required String name,
    String? description,
    required List<String> permissions,
  }) async {
    return _api.patch(
      '${ApiPaths.accessRoles}/$id',
      data: {'name': name, 'description': description, 'permissions': permissions},
      parser: (json) => AccessRoleDetail.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<void> deleteRole(int id) async {
    await _api.delete(
      '${ApiPaths.accessRoles}/$id',
      parser: (_) => null,
    );
  }
}

final accessRoleRepositoryProvider = Provider<AccessRoleRepository>((ref) {
  return AccessRoleRepository(ref.watch(apiClientProvider));
});
