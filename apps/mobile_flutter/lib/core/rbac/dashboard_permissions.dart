const List<String> kDashboardWidgetPermissions = [
  'dashboard:quick_actions',
  'dashboard:inventory_distribution',
  'dashboard:brand_distribution',
  'dashboard:recent_sales',
  'dashboard:recent_inventory',
  'dashboard:recent_transfers',
  'dashboard:recent_activity',
  'dashboard:notifications',
  'dashboard:store_status',
  'dashboard:tally_status',
  'dashboard:system_status',
];

bool canViewDashboardWidget(List<String> permissions, String widget) {
  if (!permissions.contains('dashboard:view')) return false;
  if (permissions.contains(widget)) return true;
  final hasGranular = kDashboardWidgetPermissions.any(permissions.contains);
  return !hasGranular;
}
