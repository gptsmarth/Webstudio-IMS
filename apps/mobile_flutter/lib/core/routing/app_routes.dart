abstract final class AppRoutes {
  static const bootstrap = '/bootstrap';
  static const connection = '/connection';
  static const login = '/login';

  static const dashboard = '/dashboard';
  static const stock = '/stock';
  static const inventory = '/inventory';
  static const sales = '/sales';
  static const catalogue = '/catalogue';
  static const more = '/more';
  static const settingsShell = '/settings';
  static const settingsUsers = '/settings/users';
  static const settingsAccessRoles = '/settings/access-roles';
  static const settingsTally = '/settings/tally';
  static const settingsAudit = '/settings/audit';
  static const settingsBackup = '/settings/backup';

  static const reports = '/more/reports';
  static const notifications = '/more/notifications';
  static const purchase = '/more/purchase';
  /// Users live under Settings only (not More hub).
  static const users = settingsUsers;
  static const backup = '/more/backup';
  static const tally = '/more/tally';
  static const tallyHistory = '/more/tally/history';
  static const settingsTallyHistory = '/settings/tally/history';
  static const audit = '/more/audit';
}
