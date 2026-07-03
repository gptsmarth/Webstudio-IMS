import { TallyReadinessPanel } from '../../components/tally/TallyReadinessPanel';
import { TallySettingsForm } from '../../components/settings/TallySettingsForm';
import { useDashboardPage } from '../../hooks/useDashboardPage';
import { useTallySettings } from '../../hooks/useTallySettings';
import { WorkspacePageBack } from '../../components/shell/WorkspacePageBack';
import { AlertCircle } from 'lucide-react';

export function TallyPage(): JSX.Element {
  const { data, loading, triggerTallySync, syncingTally } = useDashboardPage();
  const tallySettings = useTallySettings();

  return (
    <div className="tally-page animate-fade-in">
      <header className="tally-page__header">
        <WorkspacePageBack />
        <div>
          <h1 className="tally-page__title">Tally Integration</h1>
          <p className="tally-page__subtitle">
            Configure Tally connection, monitor sync health, and review invoice processing outcomes.
          </p>
        </div>
      </header>

      {tallySettings.error && (
        <div className="alert alert-danger tally-page__alert">
          <AlertCircle size={14} aria-hidden />
          <span>{tallySettings.error}</span>
        </div>
      )}

      <div className="tally-page__layout">
        <div className="tally-page__config">
          {tallySettings.loading || !tallySettings.tally ? (
            <div className="skeleton tally-panel__skeleton" />
          ) : (
            <TallySettingsForm
              tally={tallySettings.tally}
              canWrite={tallySettings.canWrite}
              saving={tallySettings.saving}
              onSave={tallySettings.saveTally}
              onSaved={tallySettings.refresh}
            />
          )}
        </div>

        <div className="tally-page__status">
          <h2 className="tally-page__section-title">Sync status</h2>
          <TallyReadinessPanel
            tally={data.tally}
            loading={loading}
            onSync={() => void triggerTallySync()}
            syncing={syncingTally}
          />
        </div>
      </div>
    </div>
  );
}
