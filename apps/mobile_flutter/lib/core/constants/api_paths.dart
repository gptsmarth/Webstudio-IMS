/// Backend API path constants — keep in sync with apps/backend routers.
abstract final class ApiPaths {
  static const healthLive = '/health/live';
  static const version = '/api/v1/version';
  static const capabilities = '/api/v1/capabilities';

  static const login = '/api/v1/auth/login';
  static const refresh = '/api/v1/auth/refresh';
  static const logout = '/api/v1/auth/logout';
  static const me = '/api/v1/auth/me';
  static const sessionPolicy = '/api/v1/auth/session-policy';
  static const passwordRecoveryPolicy = '/api/v1/auth/password-recovery-policy';
  static const setupStatus = '/api/v1/setup/status';

  static const syncState = '/api/v1/sync/state';
  static const search = '/api/v1/search';

  static const dashboard = '/api/v1/dashboard';
  static const dashboardDistribution = '/api/v1/dashboard/distribution';
  static const dashboardRecentActivity = '/api/v1/dashboard/recent-activity';

  static const inventory = '/api/v1/inventory';
  static const brands = '/api/v1/brands';
  static const locations = '/api/v1/locations';
  static const productModels = '/api/v1/product-models';
  static const sales = '/api/v1/sales';
  static const auditLogs = '/api/v1/audit_logs';
  static String auditLogsByInventory(String id) => '$auditLogs/by-inventory-item/$id';
  static String auditLogsLifecycle(String serial) => '$auditLogs/lifecycle/by-serial/${Uri.encodeComponent(serial)}';

  static const productModelsSpecLookup = '/api/v1/product-models/spec-lookup';
  static String productModelResolveImage(String id) => '/api/v1/product-models/$id/resolve-image';

  static const tallyConnectionTest = '/api/v1/integrations/tally/connection/test';
  static const tallySyncTrigger = '/api/v1/integrations/tally/sync/trigger';
  static const tallySyncRetry = '/api/v1/integrations/tally/sync/retry';
  static const tallySyncLog = '/api/v1/integrations/tally/sync-log';
  static const tallySyncHistory = '/api/v1/integrations/tally/sync/history';
  static const tallySyncHistoryExport = '/api/v1/integrations/tally/sync/history/export';

  static const settingsIntegrations = '/api/v1/settings/integrations';
  static const settingsGeneral = '/api/v1/settings/general';
  static const settingsSecurity = '/api/v1/settings/security';
  static const settingsTally = '/api/v1/settings/tally';
  static const securityDashboard = '/api/v1/security/dashboard';
  static const integrationKeys = '/api/v1/admin/integration-keys';

  static const reportsInventory = '/api/v1/reports/inventory';
  static const reportsSales = '/api/v1/reports/sales';
  static const reportsAudit = '/api/v1/reports/audit';
  static const reportsNotifications = '/api/v1/reports/notifications';
  static const reportsExport = '/api/v1/reports/export';

  static const notifications = '/api/v1/notifications';
  static const users = '/api/v1/users';
  static const usersRolePermissions = '/api/v1/users/role-permissions';
  static const accessRoles = '/api/v1/access-roles';
  static const settings = '/api/v1/settings';
  static const settingsRecoveryCenter = '/api/v1/settings/recovery/center';
  static const settingsBackupsAdminDashboard = '/api/v1/settings/backups/admin/dashboard';
  static const settingsBackupsImport = '/api/v1/settings/backups/import';
  static const settingsNotifications = '/api/v1/settings/notifications';
  static const settingsInventory = '/api/v1/settings/inventory';
  static const settingsSales = '/api/v1/settings/sales';
  static const settingsBackup = '/api/v1/settings/backup';
  static const settingsIntegrationsAiTest = '/api/v1/settings/integrations/ai/test';
  static const productImagesUpload = '/api/v1/product-images/upload';
  static const productImagesProxy = '/api/v1/product-images/proxy';
  static const tallyDashboard = '/api/v1/integrations/tally/dashboard';
  static const tallyStatus = '/api/v1/integrations/tally/status';
}
