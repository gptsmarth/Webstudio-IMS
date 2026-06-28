import { formatDateTime } from '../../lib/datetime';
import { buildAuditTimeline } from '../../lib/audit';
import type { AuditWorkspaceState } from '../../hooks/useAuditWorkspace';

interface AuditTimelineProps {
  workspace: Pick<AuditWorkspaceState, 'items' | 'loading' | 'selectedId' | 'selectEntry'>;
}

export function AuditTimeline({ workspace }: AuditTimelineProps): JSX.Element {
  const steps = buildAuditTimeline(workspace.items);

  if (workspace.loading) {
    return <p className="aud-timeline__loading">Loading timeline…</p>;
  }

  if (steps.length === 0) {
    return <p className="aud-timeline__empty">No audit events match the current filters.</p>;
  }

  return (
    <div className="aud-timeline">
      {steps.map((step, index) => (
        <div key={step.id} className="aud-timeline__item">
          <div className="aud-timeline__rail">
            <span className="aud-timeline__dot" aria-hidden />
            {index < steps.length - 1 && <span className="aud-timeline__line" aria-hidden />}
          </div>
          <button
            type="button"
            className={`aud-timeline__card ${workspace.selectedId === step.id ? 'aud-timeline__card--selected' : ''}`}
            onClick={() => workspace.selectEntry(step.id)}
          >
            <p className="aud-timeline__label">{step.label}</p>
            <p className="aud-timeline__meta">{formatDateTime(step.timestamp)}</p>
            {step.description && <p className="aud-timeline__desc">{step.description}</p>}
          </button>
        </div>
      ))}
    </div>
  );
}
