import { AlertCircle } from 'lucide-react';
import {
  DashboardActivityFeed,
  DashboardBrandDistribution,
  DashboardGreeting,
  DashboardInventoryDistribution,
  DashboardNotificationsPanel,
  DashboardQuickActions,
  DashboardRecentActivity,
  DashboardStoreStatus,
  DashboardSystemStatus,
  DashboardWidget,
} from '../../components/dashboard';
import { TallyReadinessPanel } from '../../components/tally/TallyReadinessPanel';
import { PageContainer } from '../../components/shell/TopToolbar';
import { useDashboardPage } from '../../hooks/useDashboardPage';
import { useAuthStore } from '../../store';
import { canViewDashboardWidget, P } from '../../services/PermissionService';

export function DashboardPage(): JSX.Element {
  const session = useAuthStore((state) => state.session);
  const {
    data,
    loading,
    error,
    refresh,
    markNotificationRead,
    resolveNotification,
    triggerTallySync,
    syncingTally,
  } = useDashboardPage();

  if (!session) {
    return (
      <PageContainer>
        <div className="dash-empty">
          <p className="dash-empty__title">Session unavailable</p>
          <p className="dash-empty__text">Sign in again to view the operations center.</p>
        </div>
      </PageContainer>
    );
  }

  const permissions = session.permissions;
  const can = (widget: string) => canViewDashboardWidget(permissions, widget);
  const totalAvailable =
    data.distribution?.total_available_inventory ?? data.snapshot?.total_available_inventory ?? 0;

  const showQuickActions = can(P.dashboard.quickActions);
  const showInventoryDistribution = can(P.dashboard.inventoryDistribution);
  const showBrandDistribution = can(P.dashboard.brandDistribution);
  const showRecentSales = can(P.dashboard.recentSales);
  const showRecentInventory = can(P.dashboard.recentInventory);
  const showRecentTransfers = can(P.dashboard.recentTransfers);
  const showActivityFeeds = showRecentSales || showRecentInventory || showRecentTransfers;
  const showRecentActivity = can(P.dashboard.recentActivity);
  const showNotifications = can(P.dashboard.notifications);
  const showStoreStatus = can(P.dashboard.storeStatus);
  const showTallyStatus = can(P.dashboard.tallyStatus);
  const showSystemStatus = can(P.dashboard.systemStatus);
  const showSecondaryGrid =
    showRecentActivity ||
    showNotifications ||
    showStoreStatus ||
    showTallyStatus ||
    showSystemStatus;
  const hasVisibleSections =
    showInventoryDistribution || showBrandDistribution || showActivityFeeds || showSecondaryGrid;

  return (
    <PageContainer>
      <div className="dash-page">
        <div className="dash-page__top">
          <DashboardGreeting session={session} />
          {showQuickActions && (
            <DashboardQuickActions
              permissions={permissions}
              onTallySync={triggerTallySync}
              syncingTally={syncingTally}
            />
          )}
        </div>

        {error && (
          <div className="alert alert-danger dash-page__alert">
            <AlertCircle size={14} aria-hidden />
            <span>{error}</span>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => void refresh()}>
              Retry
            </button>
          </div>
        )}

        {!hasVisibleSections && (
          <div className="dash-empty dash-page__section">
            <p className="dash-empty__title">No dashboard sections assigned</p>
            <p className="dash-empty__text">
              Your role can open the Dashboard tab but no widgets are enabled yet. Ask an
              administrator to update your access role.
            </p>
          </div>
        )}

        {showInventoryDistribution && (
          <section
            className="dash-page__section dash-page__section--primary"
            aria-labelledby="dash-inventory-distribution"
          >
            <h2 id="dash-inventory-distribution" className="dash-section-title">
              Inventory Distribution
            </h2>
            <DashboardWidget>
              <DashboardInventoryDistribution
                totalAvailable={totalAvailable}
                locations={data.distribution?.by_location ?? []}
                loading={loading}
              />
            </DashboardWidget>
          </section>
        )}

        {showBrandDistribution && (
          <section className="dash-page__section" aria-labelledby="dash-brand-distribution">
            <h2 id="dash-brand-distribution" className="dash-section-title">
              Brand Distribution
            </h2>
            <DashboardWidget>
              <DashboardBrandDistribution
                brands={data.distribution?.by_brand ?? []}
                loading={loading}
              />
            </DashboardWidget>
          </section>
        )}

        {showActivityFeeds && (
          <div className="dash-page__grid dash-page__grid--feeds">
            {showRecentSales && (
              <DashboardActivityFeed
                title="Recent Sales"
                subtitle="Latest sold units"
                items={data.activity}
                loading={loading}
                activityTypes={['manual_sale']}
              />
            )}
            {showRecentInventory && (
              <DashboardActivityFeed
                title="Recent Inventory Additions"
                subtitle="New serial numbers registered"
                items={data.activity}
                loading={loading}
                activityTypes={['inventory_created', 'create']}
              />
            )}
            {showRecentTransfers && (
              <DashboardActivityFeed
                title="Recent Transfers"
                subtitle="Location movements"
                items={data.activity}
                loading={loading}
                activityTypes={['location_transfer']}
              />
            )}
          </div>
        )}

        {showSecondaryGrid && (
          <div className="dash-page__grid">
            {showRecentActivity && (
              <DashboardRecentActivity items={data.activity} loading={loading} />
            )}

            {showNotifications && (
              <DashboardNotificationsPanel
                items={data.notifications}
                unreadCount={data.unreadCount}
                loading={loading}
                onResolve={resolveNotification}
                onMarkRead={markNotificationRead}
              />
            )}

            {showStoreStatus && (
              <DashboardWidget title="Store Status" subtitle="Operational stock by location">
                <DashboardStoreStatus
                  locations={data.distribution?.by_location ?? []}
                  loading={loading}
                />
              </DashboardWidget>
            )}

            {showTallyStatus && (
              <DashboardWidget title="Tally ERP" subtitle="Sales synchronization from Tally">
                <TallyReadinessPanel
                  tally={data.tally}
                  loading={loading}
                  onSync={triggerTallySync}
                  syncing={syncingTally}
                />
              </DashboardWidget>
            )}

            {showSystemStatus && (
              <DashboardWidget title="System Status" subtitle="API and database health">
                <DashboardSystemStatus
                  api={data.apiHealth}
                  database={data.databaseHealth}
                  loading={loading}
                />
              </DashboardWidget>
            )}
          </div>
        )}
      </div>
    </PageContainer>
  );
}
