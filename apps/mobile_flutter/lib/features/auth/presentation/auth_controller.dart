import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/api_exception.dart';
import '../../../core/network/api_client.dart';
import '../../../core/rbac/role_permissions.dart';
import '../../../core/storage/hive_cache.dart';
import '../../connection/data/server_preferences.dart';
import '../../connection/presentation/connection_controller.dart';
import '../data/auth_repository.dart';
import '../domain/auth_models.dart';

enum AuthStatus {
  unknown,
  unauthenticated,
  authenticating,
  authenticated,
  sessionExpired,
}

class AuthState {
  const AuthState({
    required this.status,
    this.user,
    this.errorMessage,
    this.statusMessage,
    this.lockoutUntil,
    this.failedAttempts = 0,
  });

  final AuthStatus status;
  final AuthUser? user;
  final String? errorMessage;
  final String? statusMessage;
  final DateTime? lockoutUntil;
  final int failedAttempts;

  bool get isAuthenticated => status == AuthStatus.authenticated && user != null;

  bool get isLockedOut =>
      lockoutUntil != null && DateTime.now().isBefore(lockoutUntil!);

  int get lockoutSecondsRemaining {
    if (!isLockedOut || lockoutUntil == null) return 0;
    return lockoutUntil!.difference(DateTime.now()).inSeconds.clamp(0, 999);
  }

  AuthState copyWith({
    AuthStatus? status,
    AuthUser? user,
    String? errorMessage,
    String? statusMessage,
    DateTime? lockoutUntil,
    int? failedAttempts,
    bool clearError = false,
    bool clearUser = false,
    bool clearStatusMessage = false,
    bool clearLockout = false,
  }) {
    return AuthState(
      status: status ?? this.status,
      user: clearUser ? null : user ?? this.user,
      errorMessage: clearError ? null : errorMessage ?? this.errorMessage,
      statusMessage: clearStatusMessage ? null : statusMessage ?? this.statusMessage,
      lockoutUntil: clearLockout ? null : lockoutUntil ?? this.lockoutUntil,
      failedAttempts: failedAttempts ?? this.failedAttempts,
    );
  }
}

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(
    apiClient: ref.watch(apiClientProvider),
    tokenStorage: ref.watch(secureTokenStorageProvider),
  );
});

final authControllerProvider = StateNotifierProvider<AuthController, AuthState>((ref) {
  return AuthController(ref);
});

class AuthController extends StateNotifier<AuthState> {
  AuthController(this._ref) : super(const AuthState(status: AuthStatus.unknown));

  final Ref _ref;

  AuthRepository get _repository => _ref.read(authRepositoryProvider);
  ServerPreferences get _credentials => _ref.read(serverPreferencesProvider);

  Future<void> bootstrap() async {
    state = state.copyWith(
      status: AuthStatus.authenticating,
      clearError: true,
      clearStatusMessage: true,
    );
    final restored = await _repository.restoreSession();
    if (restored) {
      try {
        final user = withEffectivePermissions(await _repository.getCurrentUser());
        state = AuthState(status: AuthStatus.authenticated, user: user);
      } catch (_) {
        final cached = _repository.readCachedUser();
        if (cached != null) {
          state = AuthState(status: AuthStatus.authenticated, user: withEffectivePermissions(cached));
        } else {
          state = const AuthState(status: AuthStatus.unauthenticated);
        }
      }
    } else {
      state = const AuthState(status: AuthStatus.unauthenticated);
    }
  }

  /// Keeps permissions in sync after cold start (avoids stale cached profile on device).
  Future<void> refreshProfile() async {
    if (state.status != AuthStatus.authenticated) return;
    try {
      final user = withEffectivePermissions(await _repository.getCurrentUser());
      final current = state.user;
      if (current != null &&
          current.id == user.id &&
          current.role == user.role &&
          listEquals(current.permissions, user.permissions)) {
        return;
      }
      state = AuthState(status: AuthStatus.authenticated, user: user);
    } catch (_) {
      final current = state.user;
      if (current != null && current.permissions.isEmpty) {
        final resolved = withEffectivePermissions(current);
        if (!listEquals(current.permissions, resolved.permissions)) {
          state = AuthState(status: AuthStatus.authenticated, user: resolved);
        }
      }
    }
  }

  Future<void> refreshProfileIfStale() async => refreshProfile();

  Future<void> bootstrapOffline() async {
    final cached = _repository.readCachedUser();
    if (cached == null) {
      state = const AuthState(status: AuthStatus.unauthenticated);
      return;
    }
    state = AuthState(status: AuthStatus.authenticated, user: withEffectivePermissions(cached));
  }

  void loadSavedCredentials() {
    final username = _credentials.getSavedUsername();
    final remember = _credentials.getRememberMe();
    if (username != null && remember) {
      state = state.copyWith();
    }
  }

  String? savedUsername() {
    if (!_credentials.getRememberMe()) return null;
    return _credentials.getSavedUsername();
  }

  bool get rememberMeDefault => _credentials.getRememberMe();

  Future<bool> login({
    required String username,
    required String password,
    bool rememberMe = false,
  }) async {
    if (state.isLockedOut) {
      state = state.copyWith(
        errorMessage:
            'Too many failed login attempts. Try again in ${state.lockoutSecondsRemaining}s.',
      );
      return false;
    }

    state = state.copyWith(
      status: AuthStatus.authenticating,
      clearError: true,
      statusMessage: 'Verifying credentials…',
    );

    try {
      state = state.copyWith(statusMessage: 'Establishing secure session…');
      final tokens = await _repository.login(
        username: username,
        password: password,
        rememberMe: rememberMe,
      );
      AuthUser user = tokens.user ?? await _repository.getCurrentUser();
      try {
        final profile = await _repository.getCurrentUser();
        user = AuthUser(
          id: profile.id,
          username: profile.username,
          displayName: profile.displayName ?? tokens.user?.displayName,
          role: profile.role,
          status: profile.status,
          mustChangePassword: profile.mustChangePassword,
          themePreference: profile.themePreference,
          permissions: profile.permissions,
          lastLoginAt: profile.lastLoginAt,
          createdAt: profile.createdAt,
        );
      } catch (_) {
        // Fall back to login payload when /me is unavailable.
      }

      await _credentials.setRememberMe(enabled: rememberMe, username: username);
      await HiveCache.clearEntityCaches();
      state = AuthState(
        status: AuthStatus.authenticated,
        user: withEffectivePermissions(user),
        statusMessage: 'Authentication successful.',
      );
      return true;
    } catch (error) {
      final message = _mapLoginError(error);
      final attempts = state.failedAttempts + 1;
      if (attempts >= 3) {
        state = AuthState(
          status: AuthStatus.unauthenticated,
          failedAttempts: attempts,
          lockoutUntil: DateTime.now().add(const Duration(seconds: 30)),
          errorMessage: 'Too many failed login attempts. Account access is suspended for 30 seconds.',
        );
      } else {
        state = AuthState(
          status: AuthStatus.unauthenticated,
          failedAttempts: attempts,
          errorMessage: message,
        );
      }
      return false;
    }
  }

  Future<void> logout({bool sessionExpired = false}) async {
    await _repository.logout();
    state = AuthState(
      status: sessionExpired ? AuthStatus.sessionExpired : AuthStatus.unauthenticated,
      errorMessage: sessionExpired ? 'Your session has expired. Please sign in again.' : null,
      failedAttempts: 0,
    );
  }

  Future<bool> refreshTokens() async {
    try {
      await _repository.refresh();
      final user = withEffectivePermissions(await _repository.getCurrentUser());
      state = AuthState(status: AuthStatus.authenticated, user: user);
      return true;
    } catch (_) {
      await _repository.clearLocalSession();
      state = const AuthState(
        status: AuthStatus.sessionExpired,
        errorMessage: 'Your session has expired. Please sign in again.',
      );
      return false;
    }
  }

  void clearLockoutIfExpired() {
    if (!state.isLockedOut && state.lockoutUntil != null) {
      state = state.copyWith(clearLockout: true, clearError: true, failedAttempts: 0);
    }
  }

  String _mapLoginError(Object error) {
    if (error is ApiException) {
      if (error.code == 'INVALID_CREDENTIALS' || error.message.toLowerCase().contains('invalid')) {
        return 'Invalid username or password.';
      }
      if (error.code == 'ACCOUNT_LOCKED') {
        return 'Account is temporarily locked. Try again later.';
      }
      if (error is NetworkException) {
        return 'Could not reach the server. Check your connection settings.';
      }
      return error.message;
    }
    return 'Sign in failed. Try again.';
  }
}
