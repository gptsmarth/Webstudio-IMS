import 'package:flutter_test/flutter_test.dart';

import 'package:webstudio_ims/features/auth/presentation/auth_controller.dart';

void main() {
  test('AuthState lockout countdown is derived from lockoutUntil', () {
    final state = AuthState(
      status: AuthStatus.unauthenticated,
      lockoutUntil: DateTime.now().add(const Duration(seconds: 20)),
      failedAttempts: 3,
    );

    expect(state.isLockedOut, isTrue);
    expect(state.lockoutSecondsRemaining, greaterThan(0));
    expect(state.lockoutSecondsRemaining, lessThanOrEqualTo(20));
  });
}
