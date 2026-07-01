import '../../../core/constants/api_paths.dart';
import '../../../core/errors/api_exception.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/json_map.dart';
import '../../../core/storage/hive_cache.dart';
import '../../../core/storage/secure_token_storage.dart';
import '../domain/auth_models.dart';

class AuthRepository {
  AuthRepository({
    required ApiClient apiClient,
    required SecureTokenStorage tokenStorage,
  })  : _api = apiClient,
        _tokens = tokenStorage;

  final ApiClient _api;
  final SecureTokenStorage _tokens;

  Future<AuthTokens> login({
    required String username,
    required String password,
    bool rememberMe = false,
    String deviceLabel = 'WEBSTUDIO Mobile',
  }) async {
    final tokens = await _api.post<AuthTokens>(
      ApiPaths.login,
      data: {
        'username': username,
        'password': password,
        'remember_me': rememberMe,
        'device_label': deviceLabel,
      },
      parser: (json) => AuthTokens.fromJson(asJsonMap(json)),
    );
    await _persistTokens(tokens);
    return tokens;
  }

  Future<AuthTokens> refresh() async {
    final refreshToken = await _tokens.getRefreshToken();
    if (refreshToken == null || refreshToken.isEmpty) {
      throw const AuthSessionExpiredException();
    }
    final tokens = await _api.post<AuthTokens>(
      ApiPaths.refresh,
      data: {'refresh_token': refreshToken},
      parser: (json) => AuthTokens.fromJson(asJsonMap(json)),
    );
    await _persistTokens(tokens);
    return tokens;
  }

  Future<AuthUser> getCurrentUser() async {
    final user = await _api.get<AuthUser>(
      ApiPaths.me,
      parser: (json) => AuthUser.fromJson(asJsonMap(json)),
    );
    await HiveCache.profile.put('current_user', user.toJson());
    return user;
  }

  Future<PasswordRecoveryPolicy> getPasswordRecoveryPolicy() async {
    final role = readCachedUser()?.role;
    return _api.get<PasswordRecoveryPolicy>(
      ApiPaths.passwordRecoveryPolicy,
      queryParameters: role == null ? null : {'role': role},
      parser: (json) => PasswordRecoveryPolicy.fromJson(asJsonMap(json)),
    );
  }

  Future<SessionPolicy> getSessionPolicy() async {
    return _api.get<SessionPolicy>(
      ApiPaths.sessionPolicy,
      parser: (json) => SessionPolicy.fromJson(asJsonMap(json)),
    );
  }

  Future<void> logout() async {
    final refreshToken = await _tokens.getRefreshToken();
    if (refreshToken != null) {
      try {
        await _api.post<Map<String, dynamic>>(
          ApiPaths.logout,
          data: {'refresh_token': refreshToken},
          parser: (json) => asJsonMapOrNull(json) ?? {},
        );
      } catch (_) {
        // Best-effort server logout.
      }
    }
    await clearLocalSession();
  }

  Future<void> clearLocalSession() async {
    await _tokens.clear();
    await HiveCache.clearSensitive();
    await HiveCache.clearEntityCaches();
  }

  Future<bool> restoreSession() async {
    if (!await _tokens.hasRefreshToken()) {
      return false;
    }
    try {
      if (await _tokens.isAccessTokenExpired()) {
        await refresh();
      }
      await getCurrentUser();
      return true;
    } catch (_) {
      final offlineUser = readCachedUser();
      if (offlineUser != null) {
        return true;
      }
      await clearLocalSession();
      return false;
    }
  }

  AuthUser? readCachedUser() {
    final raw = HiveCache.profile.get('current_user');
    if (raw == null) return null;
    return AuthUser.fromJson(Map<String, dynamic>.from(raw));
  }

  Future<void> _persistTokens(AuthTokens tokens) async {
    await _tokens.saveTokens(
      accessToken: tokens.accessToken,
      refreshToken: tokens.refreshToken,
      expiresInSeconds: tokens.expiresIn,
      sessionId: tokens.sessionId,
    );
    if (tokens.user != null) {
      await HiveCache.profile.put('current_user', tokens.user!.toJson());
    }
  }
}
