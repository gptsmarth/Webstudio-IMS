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

export function DashboardPage(): JSX.Element {
  const session = useAuthStore((state) => state.session);
  const { data, loading, error, refresh, markNotificationRead, resolveNotification, triggerTallySync, syncingTally } = useDashboardPage();

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

  const totalAvailable = data.distribution?.total_available_inventory ?? data.snapshot?.total_available_inventory ?? 0;

  return (
    <PageContainer>
      <div className="dash-page">
        <div className="dash-page__top">
          <DashboardGreeting session={session} />
          <DashboardQuickActions role={session.role} onTallySync={triggerTallySync} syncingTally={syncingTally} />
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

        <section className="dash-page__section dash-page__section--primary" aria-labelledby="dash-inventory-distribution">
          <h2 id="dash-inventory-distribution" className="dash-section-title">Inventory Distribution</h2>
          <DashboardWidget>
            <DashboardInventoryDistribution
              totalAvailable={totalAvailable}
              locations={data.distribution?.by_location ?? []}
              loading={loading}
            />
          </DashboardWidget>
        </section>

        <section className="dash-page__section" aria-labelledby="dash-brand-distribution">
          <h2 id="dash-brand-distribution" className="dash-section-title">Brand Distribution</h2>
          <DashboardWidget>
            <DashboardBrandDistribution brands={data.distribution?.by_brand ?? []} loading={loading} />
          </DashboardWidget>
        </section>

        <div className="dash-page__grid dash-page__grid--feeds">
          <DashboardActivityFeed
            title="Recent Sales"
            subtitle="Latest sold units"
            items={data.activity}
            loading={loading}
            activityTypes={['manual_sale']}
          />
          <DashboardActivityFeed
            title="Recent Inventory Additions"
            subtitle="New serial numbers registered"
            items={data.activity}
            loading={loading}
            activityTypes={['inventory_created', 'create']}
          />
          <DashboardActivityFeed
            title="Recent Transfers"
            subtitle="Location movements"
            items={data.activity}
            loading={loading}
            activityTypes={['location_transfer']}
          />
        </div>

        <div className="dash-page__grid">
          <DashboardRecentActivity items={data.activity} loading={loading} />

          <DashboardNotificationsPanel
            items={data.notifications}
            unreadCount={data.unreadCount}
            loading={loading}
            onResolve={resolveNotification}
            onMarkRead={markNotificationRead}
          />

          <DashboardWidget title="Store Status" subtitle="Operational stock by location">
            <DashboardStoreStatus locations={data.distribution?.by_location ?? []} loading={loading} />
          </DashboardWidget>

          <DashboardWidget title="Tally Status" subtitle="Synchronization readiness">
            <TallyReadinessPanel tally={data.tally} loading={loading} onSync={triggerTallySync} syncing={syncingTally} />
          </DashboardWidget>

          <DashboardWidget title="System Status" subtitle="API and database health">
            <DashboardSystemStatus api={data.apiHealth} database={data.databaseHealth} loading={loading} />
          </DashboardWidget>
        </div>
      </div>
    </PageContainer>
  );
}
