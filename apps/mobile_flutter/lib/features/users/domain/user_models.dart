import 'package:equatable/equatable.dart';

class UserSummary extends Equatable {
  const UserSummary({
    required this.id,
    required this.username,
    this.displayName,
    required this.role,
    required this.status,
    required this.isLocked,
    required this.isArchived,
    this.lastLoginAt,
    required this.activeSessionCount,
  });

  final int id;
  final String username;
  final String? displayName;
  final String role;
  final String status;
  final bool isLocked;
  final bool isArchived;
  final String? lastLoginAt;
  final int activeSessionCount;

  String get displayLabel => displayName?.trim().isNotEmpty == true ? displayName! : username;

  factory UserSummary.fromJson(Map<String, dynamic> json) => UserSummary(
        id: json['id'] as int,
        username: json['username'] as String,
        displayName: json['display_name'] as String?,
        role: json['role'] as String,
        status: json['status'] as String? ?? 'active',
        isLocked: json['is_locked'] as bool? ?? false,
        isArchived: json['is_archived'] as bool? ?? false,
        lastLoginAt: json['last_login_at'] as String?,
        activeSessionCount: json['active_session_count'] as int? ?? 0,
      );

  @override
  List<Object?> get props => [id, username, role, status];
}

class UserDetail extends Equatable {
  const UserDetail({
    required this.summary,
    required this.permissions,
    required this.sessions,
    required this.loginEvents,
    this.lockedUntil,
    this.customAccessRoleId,
    this.accessLabel,
    required this.createdAt,
    required this.updatedAt,
  });

  final UserSummary summary;
  final List<String> permissions;
  final List<UserSessionSummary> sessions;
  final List<UserLoginEventSummary> loginEvents;
  final String? lockedUntil;
  final int? customAccessRoleId;
  final String? accessLabel;
  final String createdAt;
  final String updatedAt;

  factory UserDetail.fromJson(Map<String, dynamic> json) => UserDetail(
        summary: UserSummary.fromJson(json),
        permissions: (json['permissions'] as List<dynamic>?)
                ?.map((e) => e.toString())
                .toList() ??
            const [],
        sessions: (json['sessions'] as List<dynamic>?)
                ?.whereType<Map<String, dynamic>>()
                .map(UserSessionSummary.fromJson)
                .toList() ??
            const [],
        loginEvents: (json['login_events'] as List<dynamic>?)
                ?.whereType<Map<String, dynamic>>()
                .map(UserLoginEventSummary.fromJson)
                .toList() ??
            const [],
        lockedUntil: json['locked_until'] as String?,
        customAccessRoleId: json['custom_access_role_id'] as int?,
        accessLabel: json['access_label'] as String?,
        createdAt: json['created_at'] as String? ?? '',
        updatedAt: json['updated_at'] as String? ?? '',
      );

  @override
  List<Object?> get props => [summary.id];
}

class UserSessionSummary extends Equatable {
  const UserSessionSummary({
    required this.id,
    this.deviceLabel,
    required this.createdAt,
    this.lastUsedAt,
  });

  final int id;
  final String? deviceLabel;
  final String createdAt;
  final String? lastUsedAt;

  factory UserSessionSummary.fromJson(Map<String, dynamic> json) => UserSessionSummary(
        id: json['id'] as int,
        deviceLabel: json['device_label'] as String?,
        createdAt: json['created_at'] as String,
        lastUsedAt: json['last_used_at'] as String?,
      );

  @override
  List<Object?> get props => [id];
}

class UserLoginEventSummary extends Equatable {
  const UserLoginEventSummary({
    required this.id,
    required this.success,
    this.failureReason,
    required this.createdAt,
  });

  final int id;
  final bool success;
  final String? failureReason;
  final String createdAt;

  factory UserLoginEventSummary.fromJson(Map<String, dynamic> json) => UserLoginEventSummary(
        id: json['id'] as int,
        success: json['success'] as bool? ?? false,
        failureReason: json['failure_reason'] as String?,
        createdAt: json['created_at'] as String,
      );

  @override
  List<Object?> get props => [id];
}

class UsersListFilters extends Equatable {
  const UsersListFilters({
    this.search = '',
    this.role = '',
    this.status = '',
    this.page = 1,
    this.pageSize = 25,
    this.sortField = 'created_at',
    this.sortDirection = 'desc',
  });

  final String search;
  final String role;
  final String status;
  final int page;
  final int pageSize;
  final String sortField;
  final String sortDirection;

  Map<String, dynamic> toQueryParams() => {
        'page': page,
        'page_size': pageSize,
        if (search.trim().isNotEmpty) 'search': search.trim(),
        if (role.isNotEmpty) 'role': role,
        if (status.isNotEmpty) 'status': status,
        'sort_field': sortField,
        'sort_direction': sortDirection,
      };

  UsersListFilters copyWith({String? search, int? page}) =>
      UsersListFilters(search: search ?? this.search, page: page ?? this.page);

  @override
  List<Object?> get props => [search, role, status, page];
}

String userRoleLabel(String role) => switch (role) {
      'main_admin' => 'Main admin',
      'admin' => 'Admin',
      'salesperson' => 'Salesperson',
      'service_account' => 'Service account',
      _ => role,
    };
