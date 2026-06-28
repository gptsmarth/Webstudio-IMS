import { BarChart3, ClipboardList, FileSearch, Receipt } from 'lucide-react';
import type { BuilderReportType } from '../../services/api/ReportService';

const REPORT_TYPES: Array<{
  id: BuilderReportType;
  label: string;
  description: string;
  icon: typeof ClipboardList;
}> = [
  {
    id: 'inventory',
    label: 'Inventory',
    description: 'Physical units by store, status, and date added',
    icon: ClipboardList,
  },
  {
    id: 'sales',
    label: 'Sales',
    description: 'Invoices, customers, and sale source',
    icon: Receipt,
  },
  {
    id: 'audit',
    label: 'Audit',
    description: 'User operations and system actions',
    icon: FileSearch,
  },
  {
    id: 'tally',
    label: 'Tally',
    description: 'Sync outcomes and notification events',
    icon: BarChart3,
  },
];

interface ReportTypeSelectorProps {
  value: BuilderReportType;
  onChange: (value: BuilderReportType) => void;
}

export function ReportTypeSelector({ value, onChange }: ReportTypeSelectorProps): JSX.Element {
  return (
    <fieldset className="report-builder__type">
      <legend className="report-builder__legend">Choose report type</legend>
      <div className="report-builder__type-grid">
        {REPORT_TYPES.map((option) => {
          const Icon = option.icon;
          const selected = value === option.id;
          return (
            <label
              key={option.id}
              className={`report-builder__type-card ${selected ? 'report-builder__type-card--active' : ''}`}
            >
              <input
                type="radio"
                name="report-type"
                value={option.id}
                checked={selected}
                onChange={() => onChange(option.id)}
                className="report-builder__type-input"
              />
              <Icon size={18} aria-hidden className="report-builder__type-card-icon" />
              <span className="report-builder__type-card-label">{option.label}</span>
              <span className="report-builder__type-card-desc">{option.description}</span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
