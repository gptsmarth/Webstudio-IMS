import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/presentation/auth_controller.dart';
import '../../features/auth/presentation/bootstrap_screen.dart';
import '../../features/auth/presentation/login_screen.dart';
import '../../core/rbac/mobile_navigation.dart';
import '../../core/rbac/role_permissions.dart';
import '../../features/audit/presentation/audit_center_screen.dart';
import '../../features/backup/presentation/backup_screen.dart';
import '../../features/catalogue/presentation/catalogue_screen.dart';
import '../../features/connection/presentation/connection_screen.dart';
import '../../features/dashboard/presentation/dashboard_screen.dart';
import '../../features/inventory/presentation/inventory_screen.dart';
import '../../features/notifications/presentation/notifications_screen.dart';
import '../../features/reports/presentation/reports_screen.dart';
import '../../features/sales/presentation/sales_screen.dart';
import '../../features/settings/presentation/settings_screen.dart';
import '../../features/shell/presentation/main_shell.dart';
import '../../features/shell/presentation/more_hub_screen.dart';
import '../../features/tally/presentation/tally_screen.dart';
import '../../features/users/presentation/access_roles_screen.dart';
import '../../features/users/presentation/users_screen.dart';
import 'app_routes.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final refresh = ValueNotifier<int>(0);
  ref.listen(authControllerProvider, (previous, next) {
    final shouldRefresh = previous?.status != next.status ||
        previous?.user?.id != next.user?.id ||
        previous?.user?.role != next.user?.role ||
        !listEquals(previous?.user?.permissions, next.user?.permissions);
    if (shouldRefresh) refresh.value++;
  });

  return GoRouter(
    initialLocation: AppRoutes.bootstrap,
    refreshListenable: refresh,
    redirect: (context, state) {
      final auth = ref.read(authControllerProvider);
      final path = state.matchedLocation;
      final isBootstrap = path == AppRoutes.bootstrap;
      final isConnection = path == AppRoutes.connection;
      final isLogin = path == AppRoutes.login;

      switch (auth.status) {
        case AuthStatus.unknown:
        case AuthStatus.authenticating:
          return isBootstrap ? null : AppRoutes.bootstrap;
        case AuthStatus.unauthenticated:
        case AuthStatus.sessionExpired:
          if (isLogin || isConnection) return null;
          return AppRoutes.login;
        case AuthStatus.authenticated:
          final permissions = effectivePermissions(auth.user);
          if (isBootstrap || isConnection || isLogin) {
            return defaultRouteForPermissions(permissions);
          }
          // Legacy deep links to /inventory should land on Stock for browse-only users.
          if (path == AppRoutes.inventory && isStockOnlyUser(permissions)) {
            return AppRoutes.stock;
          }
          if (!isShellPathAllowed(path, permissions)) {
            return defaultRouteForPermissions(permissions);
          }
          return null;
      }
    },
    routes: [
      GoRoute(
        path: AppRoutes.bootstrap,
        builder: (context, state) => const BootstrapScreen(),
      ),
      GoRoute(
        path: AppRoutes.connection,
        builder: (context, state) => const ConnectionScreen(),
      ),
      GoRoute(
        path: AppRoutes.login,
        builder: (context, state) => const LoginScreen(),
      ),
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) => MainShell(navigationShell: navigationShell),
        branches: [
          _shellBranch(AppRoutes.dashboard, const DashboardScreen()),
          _shellBranch(AppRoutes.stock, const InventoryScreen(stockBrowseMode: true)),
          _shellBranch(AppRoutes.inventory, const InventoryScreen()),
          _shellBranch(AppRoutes.sales, const SalesScreen()),
          _shellBranch(AppRoutes.catalogue, const CatalogueScreen()),
          _moreBranch(),
          _settingsBranch(),
        ],
      ),
    ],
  );
});

StatefulShellBranch _shellBranch(String path, Widget child) {
  return StatefulShellBranch(
    routes: [
      GoRoute(
        path: path,
        pageBuilder: (context, state) => NoTransitionPage(child: child),
      ),
    ],
  );
}

StatefulShellBranch _settingsBranch() {
  return StatefulShellBranch(
    routes: [
      GoRoute(
        path: AppRoutes.settingsShell,
        pageBuilder: (context, state) => const NoTransitionPage(child: SettingsScreen()),
        routes: [
          GoRoute(path: 'users', builder: (_, __) => const UsersScreen()),
          GoRoute(path: 'access-roles', builder: (_, __) => const AccessRolesScreen()),
          GoRoute(path: 'tally', builder: (_, __) => const TallyScreen()),
          GoRoute(path: 'audit', builder: (_, __) => const AuditCenterScreen()),
          GoRoute(path: 'backup', builder: (_, __) => const BackupScreen()),
        ],
      ),
    ],
  );
}

StatefulShellBranch _moreBranch() {
  return StatefulShellBranch(
    routes: [
      GoRoute(
        path: AppRoutes.more,
        pageBuilder: (context, state) => const NoTransitionPage(child: MoreHubScreen()),
        routes: [
          GoRoute(path: 'reports', builder: (_, __) => const ReportsScreen()),
          GoRoute(path: 'notifications', builder: (_, __) => const NotificationsScreen()),
          GoRoute(path: 'backup', builder: (_, __) => const BackupScreen()),
          GoRoute(path: 'tally', builder: (_, __) => const TallyScreen()),
          GoRoute(path: 'audit', builder: (_, __) => const AuditCenterScreen()),
        ],
      ),
    ],
  );
}
