import { useMemo } from 'react';
import { AlertCircle } from 'lucide-react';
import { SettingsCategoryPanel, SettingsNav } from '../../components/settings';
import { useSettingsWorkspace } from '../../hooks/useSettingsWorkspace';
import { canReadSettings, canWriteSettings } from '../../lib/settings';
import { useAuthStore } from '../../store';
import { WorkspacePageBack } from '../../components/shell/WorkspacePageBack';

export function SettingsPage(): JSX.Element {
  const session = useAuthStore((state) => state.session);
  const canWrite = Boolean(session && canWriteSettings(session.permissions));
  const workspace = useSettingsWorkspace(canWrite);

  const permissionDenied = useMemo(() => {
    if (!session) return 'Sign in again to access system settings.';
    if (!canReadSettings(session.permissions)) {
      return 'Your account does not have permission to view system settings.';
    }
    return null;
  }, [session]);

  if (permissionDenied || !session) {
    return (
      <div className="stg-page">
        <div className="stg-empty">
          <p className="stg-empty__title">Access restricted</p>
          <p className="stg-empty__text">
            {permissionDenied ?? 'Sign in again to access system settings.'}
          </p>
        </div>
      </div>
    );
  }

  const { permissions } = session;

  return (
    <div className="stg-page animate-fade-in">
      <header className="stg-page__header">
        <WorkspacePageBack />
        <div>
          <h1 className="stg-page__title">System Settings</h1>
          <p className="stg-page__subtitle">
            Administration control center for company profile, security, integrations, backups, and
            system health.
          </p>
        </div>
      </header>

      <div className="stg-page__panel">
        {(workspace.error || workspace.actionError) && (
          <div className="stg-page__alert alert alert-danger" role="alert">
            <AlertCircle size={16} />
            <span>{workspace.actionError ?? workspace.error}</span>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => workspace.clearActionError()}
            >
              Dismiss
            </button>
          </div>
        )}

        <div className="stg-layout">
          <SettingsNav
            active={workspace.category}
            onSelect={workspace.setCategory}
            permissions={permissions}
          />
          <div className="stg-content">
            {workspace.loading && !workspace.workspace ? (
              <p className="stg-loading">Loading settings workspace…</p>
            ) : (
              <SettingsCategoryPanel workspace={workspace} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
