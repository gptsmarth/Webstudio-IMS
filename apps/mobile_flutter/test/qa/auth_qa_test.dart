import 'package:flutter_test/flutter_test.dart';

import 'package:webstudio_ims/features/auth/domain/auth_models.dart';
import 'package:webstudio_ims/features/auth/presentation/auth_controller.dart';

void main() {
  group('QA — Authentication', () {
    test('AuthUser parses permissions and display label', () {
      final user = AuthUser.fromJson({
        'id': 1,
        'username': 'admin',
        'display_name': 'Admin User',
        'role': 'admin',
        'status': 'active',
        'must_change_password': false,
        'theme_preference': 'system',
        'permissions': ['inventory:view', 'sales:view'],
        'last_login_at': '2026-06-01T00:00:00Z',
        'created_at': '2026-01-01T00:00:00Z',
      });
      expect(user.displayLabel, 'Admin User');
      expect(user.permissions, contains('inventory:view'));
      expect(user.status, 'active');
    });

    test('AuthTokens parses expiry metadata', () {
      final tokens = AuthTokens.fromJson({
        'access_token': 'access',
        'refresh_token': 'refresh',
        'token_type': 'bearer',
        'expires_in': 3600,
        'session_id': 1,
      });
      expect(tokens.expiresIn, 3600);
      expect(tokens.sessionId, 1);
    });

    test('lockout blocks login after three failures', () {
      final state = AuthState(
        status: AuthStatus.unauthenticated,
        failedAttempts: 3,
        lockoutUntil: DateTime.now().add(const Duration(seconds: 30)),
      );
      expect(state.isLockedOut, isTrue);
      expect(state.lockoutSecondsRemaining, lessThanOrEqualTo(30));
    });

    test('session expired status is distinct from unauthenticated', () {
      const expired = AuthState(status: AuthStatus.sessionExpired);
      const fresh = AuthState(status: AuthStatus.unauthenticated);
      expect(expired.status, isNot(fresh.status));
    });
  });
}
