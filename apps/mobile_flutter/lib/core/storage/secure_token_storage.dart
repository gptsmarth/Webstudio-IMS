import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Secure JWT storage — key names aligned with desktop AuthTokenStore.
class SecureTokenStorage {
  SecureTokenStorage({FlutterSecureStorage? storage})
      : _storage = storage ??
            const FlutterSecureStorage(
              aOptions: AndroidOptions(encryptedSharedPreferences: true),
              iOptions: IOSOptions(accessibility: KeychainAccessibility.first_unlock),
            );

  static const accessTokenKey = 'webstudio_access_token';
  static const refreshTokenKey = 'webstudio_refresh_token';
  static const accessExpiresAtKey = 'webstudio_access_expires_at';
  static const sessionIdKey = 'webstudio_session_id';

  final FlutterSecureStorage _storage;

  Future<String?> getAccessToken() => _storage.read(key: accessTokenKey);

  Future<String?> getRefreshToken() => _storage.read(key: refreshTokenKey);

  Future<int?> getAccessExpiresAt() async {
    final raw = await _storage.read(key: accessExpiresAtKey);
    return raw == null ? null : int.tryParse(raw);
  }

  Future<int?> getSessionId() async {
    final raw = await _storage.read(key: sessionIdKey);
    return raw == null ? null : int.tryParse(raw);
  }

  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
    required int expiresInSeconds,
    int? sessionId,
  }) async {
    final expiresAt = DateTime.now().millisecondsSinceEpoch + (expiresInSeconds * 1000);
    await _storage.write(key: accessTokenKey, value: accessToken);
    await _storage.write(key: refreshTokenKey, value: refreshToken);
    await _storage.write(key: accessExpiresAtKey, value: expiresAt.toString());
    if (sessionId != null) {
      await _storage.write(key: sessionIdKey, value: sessionId.toString());
    }
  }

  Future<bool> hasRefreshToken() async {
    final token = await getRefreshToken();
    return token != null && token.isNotEmpty;
  }

  Future<bool> isAccessTokenExpired({int bufferSeconds = 60}) async {
    final expiresAt = await getAccessExpiresAt();
    if (expiresAt == null) return true;
    return DateTime.now().millisecondsSinceEpoch >= expiresAt - (bufferSeconds * 1000);
  }

  Future<void> clear() async {
    await _storage.delete(key: accessTokenKey);
    await _storage.delete(key: refreshTokenKey);
    await _storage.delete(key: accessExpiresAtKey);
    await _storage.delete(key: sessionIdKey);
  }
}
