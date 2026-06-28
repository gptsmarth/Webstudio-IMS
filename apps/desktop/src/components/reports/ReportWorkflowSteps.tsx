import { ClipboardList, Download, Eye, SlidersHorizontal } from 'lucide-react';

interface ReportWorkflowStepsProps {
  hasPreviewed: boolean;
}

const STEPS = [
  { id: 'type', label: 'Report type', icon: ClipboardList },
  { id: 'filters', label: 'Configure filters', icon: SlidersHorizontal },
  { id: 'preview', label: 'Preview results', icon: Eye },
  { id: 'export', label: 'Export', icon: Download },
] as const;

export function ReportWorkflowSteps({ hasPreviewed }: ReportWorkflowStepsProps): JSX.Element {
  return (
    <ol className="report-workflow" aria-label="Report builder workflow">
      {STEPS.map((step, index) => {
        const Icon = step.icon;
        const active = step.id === 'preview' && hasPreviewed;
        const complete = (step.id === 'type' || step.id === 'filters')
          || (step.id === 'preview' && hasPreviewed)
          || (step.id === 'export' && hasPreviewed);
        return (
          <li
            key={step.id}
            className={[
              'report-workflow__step',
              complete ? 'report-workflow__step--complete' : '',
              active ? 'report-workflow__step--active' : '',
            ].filter(Boolean).join(' ') || undefined}
          >
            <span className="report-workflow__index">{index + 1}</span>
            <Icon size={14} aria-hidden className="report-workflow__icon" />
            <span className="report-workflow__label">{step.label}</span>
          </li>
        );
      })}
    </ol>
  );
}
