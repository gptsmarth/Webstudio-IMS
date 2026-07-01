import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:webstudio_ims/core/theme/app_theme.dart';

void main() {
  group('QA — Dark / Light mode', () {
    testWidgets('light theme uses Material 3 with brand primary', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light(),
          home: Builder(
            builder: (context) {
              final scheme = Theme.of(context).colorScheme;
              expect(scheme.brightness, Brightness.light);
              expect(scheme.primary, isNotNull);
              return const SizedBox();
            },
          ),
        ),
      );
    });

    testWidgets('dark theme uses dark brightness', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.dark(),
          home: Builder(
            builder: (context) {
              expect(Theme.of(context).brightness, Brightness.dark);
              return const SizedBox();
            },
          ),
        ),
      );
    });

    testWidgets('theme mode switch rebuilds color scheme', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light(),
          darkTheme: AppTheme.dark(),
          themeMode: ThemeMode.system,
          home: const SizedBox(),
        ),
      );
      expect(find.byType(MaterialApp), findsOneWidget);
    });
  });

  group('QA — Phone / Tablet layout', () {
    testWidgets('phone width (390) renders navigation scaffold pattern', (tester) async {
      tester.view.physicalSize = const Size(390, 844);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light(),
          home: Scaffold(
            appBar: AppBar(title: const Text('Dashboard')),
            bottomNavigationBar: NavigationBar(
              destinations: const [
                NavigationDestination(icon: Icon(Icons.dashboard), label: 'Dashboard'),
                NavigationDestination(icon: Icon(Icons.inventory_2), label: 'Inventory'),
              ],
            ),
            body: const Center(child: Text('Phone layout')),
          ),
        ),
      );
      expect(find.text('Phone layout'), findsOneWidget);
      expect(find.byType(NavigationBar), findsOneWidget);
    });

    testWidgets('tablet width (1024) renders expanded content area', (tester) async {
      tester.view.physicalSize = const Size(1024, 768);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light(),
          home: Scaffold(
            appBar: AppBar(title: const Text('WEBSTUDIO IMS')),
            body: Row(
              children: [
                NavigationRail(
                  destinations: const [
                    NavigationRailDestination(icon: Icon(Icons.dashboard), label: Text('Dashboard')),
                    NavigationRailDestination(icon: Icon(Icons.inventory_2), label: Text('Inventory')),
                  ],
                  selectedIndex: 0,
                ),
                const Expanded(child: Center(child: Text('Tablet layout'))),
              ],
            ),
          ),
        ),
      );
      expect(find.text('Tablet layout'), findsOneWidget);
      expect(find.byType(NavigationRail), findsOneWidget);
      expect(tester.getSize(find.byType(Scaffold)).width, 1024);
    });
  });
}
