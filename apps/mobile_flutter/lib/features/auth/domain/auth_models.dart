import 'package:equatable/equatable.dart';

import '../../../core/network/json_map.dart';

class AuthUser extends Equatable {
  const AuthUser({
    required this.id,
    required this.username,
    required this.role,
    this.displayName,
    this.status = 'active',
    this.mustChangePassword = false,
    this.themePreference,
    this.permissions = const [],
    this.lastLoginAt,
    this.createdAt,
  });

  final int id;
  final String username;
  final String? displayName;
  final String role;
  final String status;
  final bool mustChangePassword;
  final String? themePreference;
  final List<String> permissions;
  final String? lastLoginAt;
  final String? createdAt;

  String get displayLabel => displayName?.trim().isNotEmpty == true ? displayName! : username;

  bool hasPermission(String permission) => permissions.contains(permission);

  factory AuthUser.fromJson(Map<String, dynamic> json) {
    return AuthUser(
      id: json['id'] as int,
      username: json['username'] as String,
      displayName: json['display_name'] as String?,
      role: json['role'] as String,
      status: json['status'] as String? ?? 'active',
      mustChangePassword: json['must_change_password'] as bool? ?? false,
      themePreference: json['theme_preference'] as String?,
      permissions: (json['permissions'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          const [],
      lastLoginAt: json['last_login_at'] as String?,
      createdAt: json['created_at'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'username': username,
        'display_name': displayName,
        'role': role,
        'status': status,
        'must_change_password': mustChangePassword,
        'theme_preference': themePreference,
        'permissions': permissions,
        'last_login_at': lastLoginAt,
        'created_at': createdAt,
      };

  @override
  List<Object?> get props => [id, username, role, permissions];
}

class AuthTokens extends Equatable {
  const AuthTokens({
    required this.accessToken,
    required this.refreshToken,
    required this.expiresIn,
    this.sessionId,
    this.user,
  });

  final String accessToken;
  final String refreshToken;
  final int expiresIn;
  final int? sessionId;
  final AuthUser? user;

  factory AuthTokens.fromJson(Map<String, dynamic> json) {
    return AuthTokens(
      accessToken: json['access_token'] as String,
      refreshToken: json['refresh_token'] as String,
      expiresIn: json['expires_in'] as int,
      sessionId: json['session_id'] as int?,
      user: asJsonMapOrNull(json['user']) != null
          ? AuthUser.fromJson(asJsonMap(json['user']))
          : null,
    );
  }

  @override
  List<Object?> get props => [accessToken, refreshToken, expiresIn, sessionId];
}

class PasswordRecoveryPolicy extends Equatable {
  const PasswordRecoveryPolicy({
    required this.selfServiceAvailable,
    required this.message,
  });

  final bool selfServiceAvailable;
  final String message;

  factory PasswordRecoveryPolicy.fromJson(Map<String, dynamic> json) {
    return PasswordRecoveryPolicy(
      selfServiceAvailable: json['self_service_available'] as bool? ?? false,
      message: json['message'] as String? ?? 'Contact your Main Administrator to reset your password.',
    );
  }

  @override
  List<Object?> get props => [selfServiceAvailable, message];
}

class SessionPolicy extends Equatable {
  const SessionPolicy({required this.sessionTimeoutMinutes});

  final int sessionTimeoutMinutes;

  factory SessionPolicy.fromJson(Map<String, dynamic> json) {
    return SessionPolicy(
      sessionTimeoutMinutes: json['session_timeout_minutes'] as int? ?? 30,
    );
  }

  @override
  List<Object?> get props => [sessionTimeoutMinutes];
}
