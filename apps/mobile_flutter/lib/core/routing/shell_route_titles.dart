import 'app_routes.dart';

class ShellRouteContext {
  const ShellRouteContext({
    required this.title,
    required this.canPopRoute,
  });

  final String title;
  final bool canPopRoute;
}

/// Resolves a human-readable shell title for nested GoRouter paths.
ShellRouteContext shellRouteContext(String location) {
  final nested = _nestedTitles.entries
      .where((entry) => location == entry.key || location.startsWith('${entry.key}/'))
      .map((entry) => entry.value)
      .firstOrNull;

  if (nested != null) {
    return ShellRouteContext(title: nested, canPopRoute: location != _branchRoot(location));
  }

  return ShellRouteContext(title: _branchTitle(location), canPopRoute: false);
}

String _branchRoot(String location) {
  if (location.startsWith(AppRoutes.settingsShell)) return AppRoutes.settingsShell;
  if (location.startsWith(AppRoutes.more)) return AppRoutes.more;
  return location;
}

String _branchTitle(String location) {
  if (location.startsWith(AppRoutes.dashboard)) return 'Dashboard';
  if (location.startsWith(AppRoutes.stock)) return 'Stock';
  if (location.startsWith(AppRoutes.inventory)) return 'Inventory';
  if (location.startsWith(AppRoutes.sales)) return 'Sales';
  if (location.startsWith(AppRoutes.catalogue)) return 'Catalogue';
  if (location.startsWith(AppRoutes.more)) return 'More';
  if (location.startsWith(AppRoutes.settingsShell)) return 'Settings';
  return 'WEBSTUDIO IMS';
}

const _nestedTitles = <String, String>{
  AppRoutes.reports: 'Reports',
  AppRoutes.notifications: 'Notifications',
  AppRoutes.purchase: 'Purchase',
  AppRoutes.backup: 'Backup',
  AppRoutes.tally: 'Tally',
  AppRoutes.audit: 'Audit',
  AppRoutes.settingsUsers: 'Users',
  AppRoutes.settingsAccessRoles: 'Access roles',
  AppRoutes.settingsTally: 'Tally',
  AppRoutes.settingsAudit: 'Audit',
  AppRoutes.settingsBackup: 'Backup',
};
