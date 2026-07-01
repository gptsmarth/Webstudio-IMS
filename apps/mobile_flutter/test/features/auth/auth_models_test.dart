import 'package:flutter_test/flutter_test.dart';
import 'package:webstudio_ims/features/auth/domain/auth_models.dart';

void main() {
  test('AuthUser parses backend user payload', () {
    final user = AuthUser.fromJson({
      'id': 1,
      'username': 'admin',
      'display_name': 'Main Admin',
      'role': 'main_admin',
      'status': 'active',
      'must_change_password': false,
      'permissions': ['inventory.view', 'sales.view'],
      'last_login_at': '2026-06-27T10:00:00Z',
      'created_at': '2026-01-01T00:00:00Z',
    });

    expect(user.id, 1);
    expect(user.displayLabel, 'Main Admin');
    expect(user.hasPermission('inventory.view'), isTrue);
    expect(user.hasPermission('users.edit'), isFalse);
  });

  test('AuthTokens parses login response', () {
    final tokens = AuthTokens.fromJson({
      'access_token': 'access',
      'refresh_token': 'refresh',
      'expires_in': 900,
      'session_id': 12,
      'user': {
        'id': 1,
        'username': 'admin',
        'role': 'main_admin',
      },
    });

    expect(tokens.accessToken, 'access');
    expect(tokens.sessionId, 12);
    expect(tokens.user?.username, 'admin');
  });
}
