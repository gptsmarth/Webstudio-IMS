import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:webstudio_ims/core/theme/app_theme.dart';

void main() {
  testWidgets('AppTheme builds Material 3 light and dark themes', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.light(),
        darkTheme: AppTheme.dark(),
        home: Builder(
          builder: (context) {
            final theme = Theme.of(context);
            expect(theme.useMaterial3, isTrue);
            expect(theme.colorScheme.primary, isNotNull);
            return const SizedBox();
          },
        ),
      ),
    );
  });
}
